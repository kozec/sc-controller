#!/usr/bin/env python2
"""
SC-Controller - App

Main application window
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, Gio, GLib, GObject
from scc.gui.controller_widget import TRIGGERS, PADS, STICKS, GYROS, BUTTONS
from scc.gui.parser import GuiActionParser, InvalidAction
from scc.gui.userdata_manager import UserDataManager
from scc.gui.daemon_manager import DaemonManager
from scc.gui.binding_editor import BindingEditor
from scc.gui.statusicon import get_status_icon
from scc.gui.dwsnc import headerbar, IS_UNITY
from scc.gui.profile_switcher import ProfileSwitcher
from scc.gui.svg_widget import SVGWidget
from scc.gui.ribar import RIBar
from scc.constants import SCButtons, STICK, STICK_PAD_MAX
from scc.constants import DAEMON_VERSION, LEFT, RIGHT
from scc.tools import get_profile_name, profile_is_default, profile_is_override
from scc.tools import check_access, find_profile, find_binary, find_gksudo, nameof
from scc.paths import get_config_path, get_profiles_path
from scc.actions import NoAction
from scc.modifiers import NameModifier
from scc.profile import Profile
from scc.config import Config

import scc.osd.menu_generators
import os, sys, platform, re, json, urllib, logging
log = logging.getLogger("App")

class App(Gtk.Application, UserDataManager, BindingEditor):
	"""
	Main application / window.
	"""
	
	IMAGE = "background.svg"
	HILIGHT_COLOR = "#FF00FF00"		# ARGB
	OBSERVE_COLOR = "#00007FFF"		# ARGB
	CONFIG = "scc.config.json"
	RELEASE_URL = "https://github.com/kozec/sc-controller/releases/tag/v%s"
	OSD_MODE_PROF_NAME = ".scc-osd.profile_editor"
	
	def __init__(self, gladepath="/usr/share/scc",
						imagepath="/usr/share/scc/images"):
		Gtk.Application.__init__(self,
				application_id="me.kozec.scc",
				flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE | Gio.ApplicationFlags.NON_UNIQUE )
		UserDataManager.__init__(self)
		BindingEditor.__init__(self, self)
		# Setup Gtk.Application
		self.setup_commandline()
		# Setup DaemonManager
		self.dm = DaemonManager()
		self.dm.connect("alive", self.on_daemon_alive)
		self.dm.connect("controller-count-changed", self.on_daemon_ccunt_changed)
		self.dm.connect("dead", self.on_daemon_dead)
		self.dm.connect("error", self.on_daemon_error)
		self.dm.connect('reconfigured', self.on_daemon_reconfigured),
		self.dm.connect("version", self.on_daemon_version)
		# Set variables
		self.config = Config()
		self.gladepath = gladepath
		self.imagepath = imagepath
		self.builder = None
		self.recursing = False
		self.statusicon = None
		self.status = "unknown"
		self.context_menu_for = None
		self.daemon_changed_profile = False
		self.osd_mode = False	# In OSD mode, only active profile can be editted
		self.osd_mode_mapper = None
		self.background = None
		self.outdated_version = None
		self.profile_switchers = []
		self.current_file = None	# Currently edited file
		self.controller_count = 0
		self.current = Profile(GuiActionParser())
		self.just_started = True
		self.button_widgets = {}
		self.hilights = { App.HILIGHT_COLOR : set(), App.OBSERVE_COLOR : set() }
		self.undo = []
		self.redo = []
	
	
	def setup_widgets(self):
		# Important stuff
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.gladepath, "app.glade"))
		self.builder.connect_signals(self)
		self.window = self.builder.get_object("window")
		self.add_window(self.window)
		self.window.set_title(_("SC Controller"))
		self.window.set_wmclass("SC Controller", "SC Controller")
		self.ribar = None
		self.create_binding_buttons()
		
		ps = self.add_switcher(10, 10)
		ps.set_allow_new(True)
		ps.set_profile(self.load_profile_selection())
		ps.connect('new-clicked', self.on_new_clicked)
		ps.connect('save-clicked', self.on_save_clicked)
		
		# Drag&drop target
		self.builder.get_object("content").drag_dest_set(Gtk.DestDefaults.ALL, [
			Gtk.TargetEntry.new("text/uri-list", Gtk.TargetFlags.OTHER_APP, 0),
			Gtk.TargetEntry.new("text/plain", Gtk.TargetFlags.OTHER_APP, 0)
			], Gdk.DragAction.COPY
		)
		
		# 'C' button
		vbc = self.builder.get_object("vbC")
		self.main_area = self.builder.get_object("mainArea")
		vbc.get_parent().remove(vbc)
		vbc.connect('size-allocate', self.on_vbc_allocated)
		
		# Background
		self.background = SVGWidget(self, os.path.join(self.imagepath, self.IMAGE))
		self.background.connect('hover', self.on_background_area_hover)
		self.background.connect('leave', self.on_background_area_hover, None)
		self.background.connect('click', self.on_background_area_click)
		self.main_area.put(self.background, 0, 0)
		self.main_area.put(vbc, 0, 0) # (self.IMAGE_SIZE[0] / 2) - 90, self.IMAGE_SIZE[1] - 100)
		
		# Test markers (those blue circles over PADs and sticks)
		self.lpadTest = Gtk.Image.new_from_file(os.path.join(self.imagepath, "test-cursor.svg"))
		self.rpadTest = Gtk.Image.new_from_file(os.path.join(self.imagepath, "test-cursor.svg"))
		self.stickTest = Gtk.Image.new_from_file(os.path.join(self.imagepath, "test-cursor.svg"))
		self.main_area.put(self.lpadTest, 40, 40)
		self.main_area.put(self.rpadTest, 290, 90)
		self.main_area.put(self.stickTest, 150, 40)
		
		# OSD mode (if used)
		if self.osd_mode:
			self.builder.get_object("btDaemon").set_sensitive(False)
			self.window.set_title(_("Edit Profile"))
		
		# Headerbar
		headerbar(self.builder.get_object("hbWindow"))
	
	
	def setup_statusicon(self):
		menu = self.builder.get_object("mnuTray")
		self.statusicon = get_status_icon(self.imagepath, menu)
		self.statusicon.connect('clicked', self.on_statusicon_clicked)
		if not self.statusicon.is_clickable():
			self.builder.get_object("mnuShowWindowTray").set_visible(True)
		GLib.idle_add(self.statusicon.set, "scc-%s" % (self.status,), _("SC Controller"))
	
	
	def destroy_statusicon(self):
		self.statusicon.destroy()
		self.statusicon = None
	
	
	def check(self):
		""" Performs various (three) checks and reports possible problems """
		# TODO: Maybe not best place to do this
		try:
			# Dynamic modules
			rawlist = file("/proc/modules", "r").read().split("\n")
			kernel_mods = [ line.split(" ")[0] for line in rawlist ]
			# Built-in modules
			release = platform.uname()[2]
			rawlist = file("/lib/modules/%s/modules.builtin" % release, "r").read().split("\n")
			kernel_mods += [ os.path.split(x)[-1].split(".")[0] for x in rawlist ]
		except Exception:
			# Maybe running on BSD or Windows...
			kernel_mods = [ ]
		
		if len(kernel_mods) > 0 and "uinput" not in kernel_mods:
			# There is no uinput
			msg = _('uinput kernel module not loaded')
			msg += "\n\n" + _('Please, consult your distribution manual on how to enable uinput')
			msg += "\n"   + _('or click on "Fix Temporary" button to attempt fix that should work until next restart.')
			ribar = self.show_error(msg)
			gksudo = find_gksudo()
			modprobe = find_binary("modprobe")
			if gksudo and not hasattr(ribar, "_fix_tmp"):
				button = Gtk.Button.new_with_label(_("Fix Temporary"))
				ribar._fix_tmp = button
				button.connect('clicked', self.apply_temporary_fix,
					gksudo + [modprobe, "uinput"],
					_("This will load missing uinput module.")
				)
				ribar.add_button(button, -1)
			return True
		elif not os.path.exists("/dev/uinput"):
			# /dev/uinput missing
			msg = _('/dev/uinput doesn\'t exists')
			msg += "\n" + _('uinput kernel module is loaded, but /dev/uinput is missing.')
			#msg += "\n\n" + _('Please, consult your distribution manual on what in the world could cause this.')
			msg += "\n\n" + _('Please, consult your distribution manual on how to enable uinput')
			self.show_error(msg)
			return True
		elif not check_access("/dev/uinput"):
			# Cannot acces uinput
			msg = _('You don\'t have required access to /dev/uinput.')
			msg += "\n"   + _('This will most likely prevent emulation from working.')
			msg += "\n\n" + _('Please, consult your distribution manual on how to enable uinput')
			msg += "\n"   + _('or click on "Fix Temporary" button to attempt fix that should work until next restart.')
			ribar = self.show_error(msg)
			gksudo = find_gksudo()
			if gksudo and not hasattr(ribar, "_fix_tmp"):
				button = Gtk.Button.new_with_label(_("Fix Temporary"))
				ribar._fix_tmp = button
				button.connect('clicked', self.apply_temporary_fix,
					gksudo + ["chmod", "666", "/dev/uinput"],
					_("This will enable input emulation for <i>every application</i> and <i>all users</i> on this machine.")
				)
				ribar.add_button(button, -1)
			return True
		return False
	
	
	def apply_temporary_fix(self, trash, shell_command, message):
		"""
		Displays MessageBox with confirmation, tries to run passed shell
		command and restarts daemon.
		
		Doing this allows user to teporary fix some uinput-related problems
		by his vaim belief I'll not format his harddrive.
		"""
		d = Gtk.MessageDialog(parent=self.window,
			flags = Gtk.DialogFlags.MODAL,
			type = Gtk.MessageType.WARNING,
			buttons = Gtk.ButtonsType.OK_CANCEL,
			message_format = _("sudo fix-my-pc")
		)
		
		def on_response(dialog, response_id):
			if response_id == -5:	# OK button, not defined anywhere
				sudo = Gio.Subprocess.new(shell_command, 0)
				sudo.communicate(None, None)
				if sudo.get_exit_status() == 0:
					self.dm.restart()
				else:
					d2 = Gtk.MessageDialog(parent=d,
						flags = Gtk.DialogFlags.MODAL,
						type = Gtk.MessageType.ERROR,
						buttons = Gtk.ButtonsType.OK,
						message_format = _("Command Failed")
					)
					d2.run()
					d2.destroy()
			d.destroy()
		
		d.connect("response", on_response)
		d.format_secondary_markup( _("""Following command is going to be executed:

<b>%s</b>

%s""") % (" ".join(shell_command), message), )
		d.show()
	
	
	def hilight(self, button):
		""" Hilights specified button on background image """
		if button:
			self.hilights[App.HILIGHT_COLOR] = set([button])
		else:
			self.hilights[App.HILIGHT_COLOR] = set()
		self._update_background()
	
	
	def _update_background(self):
		h = {}
		for color in self.hilights:
			for i in self.hilights[color]:
				h[i] = color
		self.background.hilight(h)
	
	
	def hint(self, button):
		""" As hilight, but marks GTK Button as well """
		active = None
		for b in self.button_widgets.values():
			b.widget.set_state(Gtk.StateType.NORMAL)
			if b.name == button:
				active = b.widget
		
		if active is not None:
			active.set_state(Gtk.StateType.ACTIVE)
		
		self.hilight(button)
	
	
	def show_editor(self, id):
		action = self.get_action(self.current, id)
		ae = self.choose_editor(action, "", id)
		ae.allow_first_page()
		ae.set_input(id, action)
		ae.show(self.window)
	
	
	def show_context_menu(self, for_id):
		""" Sets sensitivity of popup menu items and displays it on screen """
		mnuPopup = self.builder.get_object("mnuPopup")
		mnuCopy = self.builder.get_object("mnuCopy")
		mnuClear = self.builder.get_object("mnuClear")
		mnuPaste = self.builder.get_object("mnuPaste")
		mnuEPress = self.builder.get_object("mnuEditPress")
		mnuEPressS = self.builder.get_object("mnuEditPressSeparator")
		self.context_menu_for = for_id
		clp = Gtk.Clipboard.get_default(Gdk.Display.get_default())
		mnuCopy.set_sensitive(bool(self.get_action(self.current, for_id)))
		mnuClear.set_sensitive(bool(self.get_action(self.current, for_id)))
		mnuPaste.set_sensitive(clp.wait_is_text_available())
		mnuEPress.set_visible(for_id in STICKS + PADS)
		mnuEPressS.set_visible(mnuEPress.get_visible())
		
		mnuPopup.popup(None, None, None, None,
			3, Gtk.get_current_event_time())
	
	
	def save_config(self):
		self.config.save()
		self.dm.reconfigure()
		self.enable_test_mode()
	
	
	def on_statusicon_clicked(self, *a):
		""" Handler for user clicking on tray icon button """
		self.window.set_visible(not self.window.get_visible())
	
	
	def on_window_delete_event(self, *a):
		""" Called when user tries to close window """
		if not IS_UNITY and self.config['gui']['enable_status_icon'] and self.config['gui']['minimize_to_status_icon']:
			# Override closing and hide instead
			self.window.set_visible(False)
		else:
			self.on_mnuExit_activate()
		return True
	
	
	def on_mnuClear_activate(self, *a):
		"""
		Handler for 'Clear' context menu item.
		Simply sets NoAction to input.
		"""
		self.on_action_chosen(self.context_menu_for, NoAction())
	
	
	def on_mnuCopy_activate(self, *a):
		"""
		Handler for 'Copy' context menu item.
		Converts action to string and sends that string to clipboard.
		"""
		a = self.get_action(self.current, self.context_menu_for)
		if a:
			if a.name:
				a = NameModifier(a.name, a)
			clp = Gtk.Clipboard.get_default(Gdk.Display.get_default())
			clp.set_text(a.to_string().encode('utf-8'), -1)
			clp.store()
	
	
	def on_mnuPaste_activate(self, *a):
		"""
		Handler for 'Paste' context menu item.
		Reads string from clipboard, parses it as action and sets that action
		on selected input.
		"""
		clp = Gtk.Clipboard.get_default(Gdk.Display.get_default())
		text = clp.wait_for_text()
		if text:
			a = GuiActionParser().restart(text.decode('utf-8')).parse()
			if not isinstance(a, InvalidAction):
				self.on_action_chosen(self.context_menu_for, a)
	
	
	def on_mnuEditPress_activate(self, *a):
		"""
		Handler for 'Edit Pressed Action' context menu item.
		"""
		self.show_editor(getattr(SCButtons, self.context_menu_for))
	
	
	def on_mnuGlobalSettings_activate(self, *a):
		from scc.gui.global_settings import GlobalSettings
		gs = GlobalSettings(self)
		gs.show(self.window)
	
	
	def on_mnuImport_activate(self, *a):
		"""
		Handler for 'Import Steam Profile' context menu item.
		Displays apropriate dialog.
		"""
		from scc.gui.importexport.dialog import Dialog
		ied = Dialog(self)
		ied.show(self.window)
	
	
	def on_btUndo_clicked(self, *a):
		if len(self.undo) < 1: return
		undo, self.undo = self.undo[-1], self.undo[0:-1]
		self.set_action(self.current, undo.id, undo.before)
		self.redo.append(undo)
		self.builder.get_object("btRedo").set_sensitive(True)
		if len(self.undo) < 1:
			self.builder.get_object("btUndo").set_sensitive(False)
		self.on_profile_modified()
	
	
	def on_btRedo_clicked(self, *a):
		if len(self.redo) < 1: return
		redo, self.redo = self.redo[-1], self.redo[0:-1]
		self.set_action(self.current, redo.id, redo.after)
		self.undo.append(redo)
		self.builder.get_object("btUndo").set_sensitive(True)
		if len(self.redo) < 1:
			self.builder.get_object("btRedo").set_sensitive(False)
		self.on_profile_modified()
	
	
	def on_profiles_loaded(self, profiles):
		for ps in self.profile_switchers:
			ps.set_profile_list(profiles)
	
	
	def undeletable_dialog(self, dlg, *a):
		dlg.hide()
		return True
	
	
	def on_btNewProfile_clicked(self, *a):
		""" Called when new profile name is set and OK is clicked """
		txNewProfile = self.builder.get_object("txNewProfile")
		rbNewProfile = self.builder.get_object("rbNewProfile")
		
		dlg = self.builder.get_object("dlgNewProfile")
		if rbNewProfile.get_active():
			# Creating blank profile is requested
			self.current.clear()
		else:
			self.current.is_template = False
		self.new_profile(self.current, txNewProfile.get_text())
		dlg.hide()
	
	
	def on_rbNewProfile_group_changed(self, *a):
		"""
		Called when user clicks 'Copy current profile' button.
		If profile name was not changed by user before clicking it,
		it's automatically changed.
		"""
		txNewProfile = self.builder.get_object("txNewProfile")
		rbNewProfile = self.builder.get_object("rbNewProfile")
		
		if not txNewProfile._changed:
			self.recursing = True
			if rbNewProfile.get_active():
				# Create empty profile
				txNewProfile.set_text(self.generate_new_name())
			else:
				# Copy current profile
				txNewProfile.set_text(self.generate_copy_name(txNewProfile._name))
			self.recursing = False
	
	
	def on_profile_modified(self, update_ui=True):
		"""
		Called when selected profile is modified in memory.
		"""
		if update_ui:
			self.profile_switchers[0].set_profile_modified(True, self.current.is_template)
		
		if not self.current_file.get_path().endswith(".mod"):
			mod = self.current_file.get_path() + ".mod"
			self.current_file = Gio.File.new_for_path(mod)
		
		self.save_profile(self.current_file, self.current)
	
	
	def on_profile_loaded(self, profile, giofile):
		self.current = profile
		self.current_file = giofile
		self.recursing = True
		self.profile_switchers[0].set_profile_modified(False, self.current.is_template)
		self.builder.get_object("txProfileFilename").set_text(giofile.get_path())
		self.builder.get_object("txProfileDescription").get_buffer().set_text(self.current.description)
		self.builder.get_object("cbProfileIsTemplate").set_active(self.current.is_template)
		for b in self.button_widgets.values():
			b.update()
		self.recursing = False
	
	
	def on_profile_selected(self, ps, name, giofile):
		if ps == self.profile_switchers[0]:
			self.load_profile(giofile)
		if ps.get_controller():
			ps.get_controller().set_profile(giofile.get_path())
	
	
	def on_unknown_profile(self, ps, name):
		log.warn("Daemon reported unknown profile: '%s'; Overriding.", name)
		if self.current_file is not None:
			ps.get_controller().set_profile(self.current_file.get_path())
	
	
	def on_save_clicked(self, *a):
		if self.current_file.get_path().endswith(".mod"):
			orig = self.current_file.get_path()[0:-4]
			self.current_file = Gio.File.new_for_path(orig)
		
		if self.current.is_template:
			# Ask user if he is OK with overwriting template
			d = Gtk.MessageDialog(parent=self.window,
				flags = Gtk.DialogFlags.MODAL,
				type = Gtk.MessageType.QUESTION,
				buttons = Gtk.ButtonsType.YES_NO,
				message_format = _("You are about to save changes over template.\nAre you sure?")
			)
			NEW_PROFILE_BUTTON = 7
			d.add_button(_("Create New Profile"), NEW_PROFILE_BUTTON)
			
			
			r = d.run()
			d.destroy()
			if r == NEW_PROFILE_BUTTON:
				# New profile button clicked
				ps = self.profile_switchers[0]
				rbCopyProfile = self.builder.get_object("rbCopyProfile")
				self.on_new_clicked(ps, ps.get_profile_name())
				rbCopyProfile.set_active(True)
				return
			if r != -8:
				# Bail out if user answers anything but yes
				return
		
		self.save_profile(self.current_file, self.current)
	
	
	def on_profile_saved(self, giofile, send=True):
		"""
		Called when selected profile is saved to disk
		"""
		if self.osd_mode:
			# Special case, profile shouldn't be changed while in osd_mode
			return
		
		if giofile.get_path().endswith(".mod"):
			# Special case, this one is saved only to be sent to daemon
			# and user doesn't need to know about it
			if self.dm.is_alive():
				self.dm.set_profile(giofile.get_path())
			return
		
		self.profile_switchers[0].set_profile_modified(False, self.current.is_template)
		if send and self.dm.is_alive() and not self.daemon_changed_profile:
			self.dm.set_profile(giofile.get_path())
		
		self.current_file = giofile	
	
	
	def generate_new_name(self):
		"""
		Generates name for new profile.
		That is 'New Profile X', where X is number that makes name unique.
		"""
		i = 1
		new_name = _("New Profile %s") % (i,)
		filename = os.path.join(get_profiles_path(), new_name + ".sccprofile")
		while os.path.exists(filename):
			i += 1
			new_name = _("New Profile %s") % (i,)
			filename = os.path.join(get_profiles_path(), new_name + ".sccprofile")
		return new_name
	
	
	def generate_copy_name(self, name):
		"""
		Generates name for profile copy.
		That is 'New Profile X', where X is number that makes name unique.
		"""
		new_name = _("%s (copy)") % (name,)
		filename = os.path.join(get_profiles_path(), new_name + ".sccprofile")
		i = 2
		while os.path.exists(filename):
			new_name = _("%s (copy %s)") % (name,)
			filename = os.path.join(get_profiles_path(), new_name + ".sccprofile")
			i += 1
		return new_name
	
	
	def on_txNewProfile_changed(self, tx):
		if self.recursing:
			return
		tx._changed = True
	
	
	def on_new_clicked(self, ps, name):
		dlg = self.builder.get_object("dlgNewProfile")
		txNewProfile = self.builder.get_object("txNewProfile")
		rbNewProfile = self.builder.get_object("rbNewProfile")
		self.recursing = True
		rbNewProfile.set_active(True)
		txNewProfile.set_text(self.generate_new_name())
		txNewProfile._name = name
		txNewProfile._changed = False
		self.recursing = False
		dlg.set_transient_for(self.window)
		dlg.show()
	
	
	def on_action_chosen(self, id, action, mark_changed=True):
		before = self.set_action(self.current, id, action)
		if mark_changed:
			if before.to_string() != action.to_string():
				# TODO: Maybe better comparison
				self.undo.append(UndoRedo(id, before, action))
				self.builder.get_object("btUndo").set_sensitive(True)
			self.on_profile_modified()
		else:
			self.on_profile_modified(update_ui=False)
		return before
	
	
	def on_background_area_hover(self, trash, area):
		self.hint(area)
	
	
	def on_background_area_click(self, trash, area):
		if area in [ x.name for x in BUTTONS ]:
			self.hint(None)
			self.show_editor(getattr(SCButtons, area))
		elif area in TRIGGERS + STICKS + PADS:
			self.hint(None)
			self.show_editor(area)
	
	
	def on_vbc_allocated(self, vbc, allocation):
		"""
		Called when size of 'Button C' is changed. Centers button
		on background image
		"""
		main_area = self.builder.get_object("mainArea")
		x = (main_area.get_allocation().width - allocation.width) / 2
		y = main_area.get_allocation().height - allocation.height
		main_area.move(vbc, x, y)
	
	
	def on_ebImage_motion_notify_event(self, box, event):
		self.background.on_mouse_moved(event.x, event.y)
	
	
	def on_exiting_n_daemon_killed(self, *a):
		self.quit()
	
	
	def on_mnuExit_activate(self, *a):
		if self.app.config['gui']['autokill_daemon']:
			log.debug("Terminating scc-daemon")
			for x in ("content", "mnuEmulationEnabled", "mnuEmulationEnabledTray"):
				w = self.builder.get_object(x)
				w.set_sensitive(False)
			self.set_daemon_status("unknown", False)
			self.hide_error()
			if self.dm.is_alive():
				self.dm.connect("dead", self.on_exiting_n_daemon_killed)
				self.dm.connect("error", self.on_exiting_n_daemon_killed)
				self.dm.stop()
			else:
				# Daemon appears to be dead, kill it just in case
				self.dm.stop()
				self.quit()
		else:
			self.quit()
	
	
	def on_mnuAbout_activate(self, *a):
		from scc.gui.aboutdialog import AboutDialog
		AboutDialog(self).show(self.window)
	
	
	def on_daemon_alive(self, *a):
		self.set_daemon_status("alive", True)
		if not self.release_notes_visible():
			self.hide_error()
		self.just_started = False
		if self.osd_mode:
			self.enable_osd_mode()
		elif self.profile_switchers[0].get_file() is not None and not self.just_started:
			self.dm.set_profile(self.current_file.get_path())
		GLib.timeout_add_seconds(1, self.check)
		self.enable_test_mode()
	
	
	def on_daemon_ccunt_changed(self, daemon, count):
		if (self.controller_count, count) == (0, 1):
			# First controller connected
			# 
			# 'event' signal should be connected only on first controller,
			# so this block is executed only when number of connected
			# controllers changes from 0 to 1
			c = self.dm.get_controllers()[0]
			c.connect('event', self.on_daemon_event_observer)
		elif count > self.controller_count:
			# Controller added
			while len(self.profile_switchers) < count:
				s = self.add_switcher()
		elif count < self.controller_count:
			# Controller removed
			while len(self.profile_switchers) > max(1, count):
				s = self.profile_switchers.pop()
				s.set_controller(None)
				self.remove_switcher(s)
		
		# Assign controllers to widgets
		for i in xrange(0, count):
			c = self.dm.get_controllers()[i]
			self.profile_switchers[i].set_controller(c)
		
		if count < 1:
			# Special case, no controllers are connected, but one widget
			# has to stay on screen
			self.profile_switchers[0].set_controller(None)
		
		self.controller_count = count
	
	
	def new_profile(self, profile, name):
		filename = os.path.join(get_profiles_path(), name + ".sccprofile")
		self.current_file = Gio.File.new_for_path(filename)
		self.save_profile(self.current_file, profile)
	
	
	def add_switcher(self, margin_left=30, margin_right=40, margin_bottom=2):
		"""
		Adds new profile switcher widgets on top of window. Called
		when new controller is connected to daemon.
		
		Returns generated ProfileSwitcher instance.
		"""
		vbAllProfiles = self.builder.get_object("vbAllProfiles")
		
		ps = ProfileSwitcher(self.imagepath, self.config)
		ps.set_margin_left(margin_left)
		ps.set_margin_right(margin_right)
		ps.set_margin_bottom(margin_bottom)
		ps.connect('right-clicked', self.on_profile_right_clicked)
		
		vbAllProfiles.pack_start(ps, False, False, 0)
		vbAllProfiles.reorder_child(ps, 0)
		vbAllProfiles.show_all()
		
		if self.osd_mode:
			ps.set_allow_switch(False)
		
		if len(self.profile_switchers) > 0:
			ps.set_profile_list(self.profile_switchers[0].get_profile_list())
		
		self.profile_switchers.append(ps)
		ps.connect('changed', self.on_profile_selected)
		ps.connect('unknown-profile', self.on_unknown_profile)
		return ps
	
	
	def remove_switcher(self, s):
		"""
		Removes given profile switcher from UI.
		"""
		vbAllProfiles = self.builder.get_object("vbAllProfiles")
		vbAllProfiles.remove(s)
		s.destroy()
	
	
	def enable_test_mode(self):
		"""
		Disables and re-enables Input Test mode. If sniffing is disabled in
		daemon configuration, 2nd call fails and logs error.
		"""
		if self.dm.is_alive() and not self.osd_mode:
			try:
				c = self.dm.get_controllers()[0]
			except IndexError:
				# Zero controllers
				return
			c.unlock_all()
			c.observe(DaemonManager.nocallback, self.on_observe_failed,
				'A', 'B', 'C', 'X', 'Y', 'START', 'BACK', 'LB', 'RB',
				'LPAD', 'RPAD', 'LGRIP', 'RGRIP', 'LT', 'RT', 'LEFT',
				'RIGHT', 'STICK', 'STICKPRESS')
	
	
	def enable_osd_mode(self):
		# TODO: Support for multiple controllers here
		self.osd_mode_controller = 0
		osd_mode_profile = Profile(GuiActionParser())
		osd_mode_profile.load(find_profile(App.OSD_MODE_PROF_NAME))
		try:
			c = self.dm.get_controllers()[self.osd_mode_controller]
		except IndexError:
			log.error("osd_mode: Controller not connected")
			self.quit()
			return
		
		def on_lock_failed(*a):
			log.error("osd_mode: Locking failed")
			self.quit()
		
		def on_lock_success(*a):
			log.debug("osd_mode: Locked everything")
			from scc.gui.osd_mode_mapper import OSDModeMapper
			self.osd_mode_mapper = OSDModeMapper(osd_mode_profile)
			self.osd_mode_mapper.set_target_window(self.window.get_window())
			GLib.timeout_add(10, self.osd_mode_mapper.run_scheduled)
		
		# Locks everything but pads. Pads are emulating mouse and this is
		# better left in daemon - involving socket in mouse controls
		# adds too much lags.
		c.lock(on_lock_success, on_lock_failed,
			'A', 'B', 'X', 'Y', 'START', 'BACK', 'LB', 'RB', 'C', 'LPAD', 'RPAD',
			'STICK', 'LGRIP', 'RGRIP', 'LT', 'RT', 'STICKPRESS')
		
		# Ask daemon to temporaly reconfigure pads for mouse emulation
		c.replace(DaemonManager.nocallback, on_lock_failed,
			LEFT, osd_mode_profile.pads[LEFT])
		c.replace(DaemonManager.nocallback, on_lock_failed,
			RIGHT, osd_mode_profile.pads[RIGHT])
	
	
	def on_observe_failed(self, error):
		log.debug("Failed to enable test mode: %s", error)
	
	
	def on_daemon_version(self, daemon, version):
		"""
		Checks if reported version matches expected one.
		If not, daemon is restarted.
		"""
		if version != DAEMON_VERSION and self.outdated_version != version:
			log.warning(
				"Running daemon instance is too old (version %s, expected %s). Restarting...",
				version, DAEMON_VERSION)
			self.outdated_version = version
			self.set_daemon_status("unknown", False)
			self.dm.restart()
		else:
			# At this point, correct daemon version of daemon is running
			# and we can check if there is anything new to inform user about
			if self.app.config['gui']['news']['last_version'] != App.get_release():
				if self.app.config['gui']['news']['enabled']:
					if not self.osd_mode:
						self.check_release_notes()
	
	
	def on_daemon_error(self, daemon, error):
		log.debug("Daemon reported error '%s'", error)
		msg = _('There was an error with enabling emulation: <b>%s</b>') % (error,)
		# Known errors are handled with aditional message
		if "Device not found" in error:
			msg += "\n" + _("Please, check if you have reciever dongle connected to USB port.")
		elif "LIBUSB_ERROR_ACCESS" in error:
			msg += "\n" + _("You don't have access to controller device.")
			msg += "\n\n" + ( _("Consult your distribution manual, try installing Steam package or <a href='%s'>install required udev rules manually</a>.") %
					'https://wiki.archlinux.org/index.php/Gamepad#Steam_Controller_Not_Pairing' )
			# TODO: Write howto somewhere instead of linking to ArchWiki
		elif "LIBUSB_ERROR_BUSY" in error:
			msg += "\n" + _("Another application (most likely Steam) is using the controller.")
		elif "LIBUSB_ERROR_PIPE" in error:
			msg += "\n" + _("USB dongle was removed.")
		elif "Failed to create uinput device." in error:
			# Call check() method and try to determine what went wrong.
			if self.check():
				# Check() returns True if error was "handled".
				return
			# If check() fails to find error reason, error message is displayed as it is
		
		if self.osd_mode:
			self.quit()
		
		self.show_error(msg)
		self.set_daemon_status("error", True)
	
	
	def on_daemon_event_observer(self, daemon, what, data):
		if self.osd_mode_mapper:
			self.osd_mode_mapper.handle_event(daemon, what, data)
		elif what in (LEFT, RIGHT, STICK):
			widget, area = {
				LEFT  : (self.lpadTest,  "LPADTEST"),
				RIGHT : (self.rpadTest,  "RPADTEST"),
				STICK : (self.stickTest, "STICKTEST"),
			}[what]
			# Check if stick or pad is released
			if data[0] == data[1] == 0:
				widget.hide()
				return
			if not widget.is_visible():
				widget.show()
			# Grab values
			ax, ay, aw, trash = self.background.get_area_position(area)
			cw = widget.get_allocation().width
			# Compute center
			x, y = ax + aw * 0.5 - cw * 0.5, ay + 1.0 - cw * 0.5
			# Add pad position
			x += data[0] * aw / STICK_PAD_MAX * 0.5
			y -= data[1] * aw / STICK_PAD_MAX * 0.5
			# Move circle
			self.main_area.move(widget, x, y)
		elif what in ("LT", "RT", "STICKPRESS"):
			what = {
				"LT" : "LEFT",
				"RT" : "RIGHT",
				"STICKPRESS" : "STICK"
			}[what]
			if data[0]:
				self.hilights[App.OBSERVE_COLOR].add(what)
			else:
				self.hilights[App.OBSERVE_COLOR].remove(what)
			self._update_background()
		elif hasattr(SCButtons, what):
			try:
				if data[0]:
					self.hilights[App.OBSERVE_COLOR].add(what)
				else:
					self.hilights[App.OBSERVE_COLOR].remove(what)
				self._update_background()
			except KeyError, e:
				# Non fatal
				pass
		else:
			print "event", what
	
	
	def on_profile_right_clicked(self, ps):
		for name in ("mnuConfigureController", "mnuTurnoffController"):
			# Disable controller-related menu items if controller is not connected
			obj = self.builder.get_object(name)
			obj.set_sensitive(ps.get_controller() is not None)
		
		for name in ("mnuProfileNew", "mnuProfileCopy", "mnuProfileRename",
					"mnuProfileDetails", "mnuProfileSeparator1",
					"mnuProfileSeparator2"):
			# Hide profile-related menu items for all but 1st profile switcher
			obj = self.builder.get_object(name)
			obj.set_visible(ps == self.profile_switchers[0])
		
		if ps == self.profile_switchers[0]:
			name = ps.get_profile_name()
			is_override = profile_is_override(name)
			is_default = profile_is_default(name)
			self.builder.get_object("mnuProfileDelete").set_visible(not is_default)
			self.builder.get_object("mnuProfileRevert").set_visible(is_override)
			self.builder.get_object("mnuProfileRename").set_visible(not is_default)
		else:
			self.builder.get_object("mnuProfileDelete").set_visible(False)
			self.builder.get_object("mnuProfileRevert").set_visible(False)
		
		mnuPS = self.builder.get_object("mnuPS")
		mnuPS.ps = ps
		mnuPS.popup(None, None, None, None,
			3, Gtk.get_current_event_time())
	
	
	def on_mnuConfigureController_activate(self, *a):
		from scc.gui.controller_settings import ControllerSettings
		mnuPS = self.builder.get_object("mnuPS")
		cs = ControllerSettings(self, mnuPS.ps.get_controller(), mnuPS.ps)
		cs.show(self.window)
	
	
	def on_mnuProfileNew_activate(self, *a):
		mnuPS = self.builder.get_object("mnuPS")
		self.on_new_clicked(mnuPS.ps, mnuPS.ps.get_name())
	
	
	def on_mnuProfileCopy_activate(self, *a):
		mnuPS = self.builder.get_object("mnuPS")
		rbCopyProfile = self.builder.get_object("rbCopyProfile")
		self.on_new_clicked(mnuPS.ps, mnuPS.ps.get_profile_name())
		rbCopyProfile.set_active(True)
	
	
	def on_mnuProfileDetails_activate(self, *a):
		self.builder.get_object("dlgProfileDetails").show()
	
	
	def on_mnuProfileRename_activate(self, *a):
		dlg = self.builder.get_object("dlgRenameProfile")
		txRename = self.builder.get_object("txRename")
		mnuPS = self.builder.get_object("mnuPS")
		name = mnuPS.ps.get_profile_name()
		txRename.set_text(name)
		dlg._name = name
		dlg.set_transient_for(self.window)
		dlg.show()
	
	
	def on_txRename_changed(self, tx):
		name = tx.get_text()
		btRenameProfile = self.builder.get_object("btRenameProfile")
		btRenameProfile.set_sensitive(find_profile(name) is None)
	
	
	def on_btRenameProfile_clicked(self, *a):
		dlg = self.builder.get_object("dlgRenameProfile")
		txRename = self.builder.get_object("txRename")
		old_name = dlg._name
		new_name = txRename.get_text()
		old_fname = os.path.join(get_profiles_path(), old_name + ".sccprofile")
		new_fname = os.path.join(get_profiles_path(), new_name + ".sccprofile")
		try:
			os.rename(old_fname, new_fname)
			for n in (old_fname, new_fname):
				try:
					os.unlink(n + ".mod")
				except:
					# non-existing .mod file is expected
					pass
		except Exception, e:
			log.error("Failed to rename %s: %s", old_fname, e)
		
		controllers = list(self.dm.get_controllers())
		for c in controllers:
			if get_profile_name(c.get_profile()) == old_name:
				ps = self.profile_switchers[controllers.index(c)]
				ps.set_profile(new_name, True)
				c.set_profile(new_name)
		self.load_profile_list()
		dlg.hide()
	
	
	def on_mnuProfileDelete_activate(self, *a):
		mnuPS = self.builder.get_object("mnuPS")
		name = mnuPS.ps.get_profile_name()
		is_override = profile_is_override(name)
		
		if is_override:
			text = _("Really revert current profile to default values?")
		else:
			text = _("Really delete current profile?")
		
		d = Gtk.MessageDialog(parent=self.window,
			flags = Gtk.DialogFlags.MODAL,
			type = Gtk.MessageType.WARNING,
			buttons = Gtk.ButtonsType.OK_CANCEL,
			message_format = text,
		)
		d.format_secondary_text(_("This action is not undoable!"))
		
		if d.run() == -5: # OK button, no idea where is this defined...
			fname = os.path.join(get_profiles_path(), name + ".sccprofile")
			try:
				os.unlink(fname)
				try:
					os.unlink(fname + ".mod")
				except:
					# non-existing .mod file is expected
					pass
				for ps in self.profile_switchers:
					ps.refresh_profile_path(name)
			except Exception, e:
				log.error("Failed to remove %s: %s", fname, e)
		d.destroy()
	
	
	def mnuTurnoffController_activate(self, *a):
		mnuPS = self.builder.get_object("mnuPS")
		if mnuPS.ps.get_controller():
			mnuPS.ps.get_controller().turnoff()
	
	
	def show_error(self, message, ribar=None):
		if self.ribar is None:
			self.ribar = ribar or RIBar(message, Gtk.MessageType.ERROR)
			content = self.builder.get_object("content")
			content.pack_start(self.ribar, False, False, 1)
			content.reorder_child(self.ribar, 0)
			self.ribar.connect("close", self.hide_error)
			self.ribar.connect("response", self.hide_error)
		else:
			self.ribar.get_label().set_markup(message)
		self.ribar.show()
		self.ribar.set_reveal_child(True)
		return self.ribar
	
	
	def hide_error(self, *a):
		if self.ribar is not None:
			if self.ribar.get_parent() is not None:
				self.ribar.get_parent().remove(self.ribar)
		self.ribar = None
	
	
	def on_daemon_reconfigured(self, *a):
		log.debug("Reloading config...")
		self.config.reload()
		for ps in self.profile_switchers:
			ps.set_controller(ps.get_controller())
	
	
	def on_daemon_dead(self, *a):
		if self.just_started:
			self.dm.restart()
			self.just_started = False
			self.set_daemon_status("unknown", True)
			return
		
		if self.osd_mode:
			self.quit()
		
		for ps in self.profile_switchers:
			ps.set_controller(None)
			ps.on_daemon_dead()
		self.set_daemon_status("dead", False)
	
	
	def on_mnuEmulationEnabled_toggled(self, cb):
		if self.recursing : return
		if cb.get_active():
			# Turning daemon on
			self.set_daemon_status("unknown", True)
			cb.set_sensitive(False)
			self.dm.start()
		else:
			# Turning daemon off
			self.set_daemon_status("unknown", False)
			cb.set_sensitive(False)
			self.hide_error()
			self.dm.stop()
			
	
	def do_startup(self, *a):
		Gtk.Application.do_startup(self, *a)
		self.load_profile_list()
		self.setup_widgets()
		if self.app.config['gui']['enable_status_icon']:
			self.setup_statusicon()
		self.set_daemon_status("unknown", True)
	
	
	def do_local_options(self, trash, lo):
		set_logging_level(lo.contains("verbose"), lo.contains("debug") )
		self.osd_mode = lo.contains("osd")
		return -1
	
	
	def do_command_line(self, cl):
		Gtk.Application.do_command_line(self, cl)
		if len(cl.get_arguments()) > 1:
			filename = " ".join(cl.get_arguments()[1:]) # 'cos fuck Gtk...
			from scc.gui.importexport.dialog import Dialog
			if Dialog.determine_type(filename) is not None:
				ied = Dialog(self)
				def i_told_you_to_quit(*a):
					sys.exit(0)
				ied.window.connect('destroy', i_told_you_to_quit)
				ied.show(self.window)
				# Skip first screen and try to import this file
				ied.import_file(filename)
			else:
				sys.exit(1)
		else:
			self.activate()
		return 0
	
	
	def do_activate(self, *a):
		if (not IS_UNITY and self.app.config['gui']['enable_status_icon']
							and self.app.config['gui']['minimize_on_start']):
			log.info("")
			log.info(_("SC-Controller started and running in notification area"))
		else:
			self.builder.get_object("window").show()
	
	
	def remove_dot_profile(self):
		"""
		Checks if first profile in list begins with dot and if yes, removes it.
		This is done to undo automatic addition that is done when daemon reports
		selecting such profile.
		"""
		cb = self.builder.get_object("cbProfile")
		model = cb.get_model()
		if len(model) == 0:
			# Nothing to remove
			return
		if not model[0][0].startswith("."):
			# Not dot profile
			return
		active = model.get_path(cb.get_active_iter())
		first = model[0].path
		if active == first:
			# Can't remove active item
			return
		model.remove(model[0].iter)
	
	
	def get_current_profile(self):
		return self.profile_switchers[0].get_profile_name()
	
	
	def set_daemon_status(self, status, daemon_runs):
		""" Updates image that shows daemon status and menu shown when image is clicked """
		log.debug("daemon status: %s", status)
		icon = os.path.join(self.imagepath, "scc-%s.svg" % (status,))
		imgDaemonStatus = self.builder.get_object("imgDaemonStatus")
		btDaemon = self.builder.get_object("btDaemon")
		mnuEmulationEnabled = self.builder.get_object("mnuEmulationEnabled")
		mnuEmulationEnabledTray = self.builder.get_object("mnuEmulationEnabledTray")
		imgDaemonStatus.set_from_file(icon)
		mnuEmulationEnabled.set_sensitive(True)
		mnuEmulationEnabledTray.set_sensitive(True)
		self.window.set_icon_from_file(icon)
		self.status = status
		if self.statusicon:
			GLib.idle_add(self.statusicon.set, "scc-%s" % (self.status,), _("SC Controller"))
		self.recursing = True
		if status == "alive":
			btDaemon.set_tooltip_text(_("Emulation is active"))
		elif status == "error":
			btDaemon.set_tooltip_text(_("Error enabling emulation"))
		elif status == "dead":
			btDaemon.set_tooltip_text(_("Emulation is inactive"))
		else:
			btDaemon.set_tooltip_text(_("Checking emulation status..."))
		mnuEmulationEnabled.set_active(daemon_runs)
		mnuEmulationEnabledTray.set_active(daemon_runs)
		self.recursing = False
	
	
	def on_btCloseDetails_clicked(self, *a):
		self.builder.get_object("dlgProfileDetails").hide()
	
	
	def on_buffProfileDescription_changed(self, buffer, *a):
		if self.recursing: return
		self.current.description = buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)
		self.on_profile_modified()
	
	def on_cbProfileIsTemplate_toggled(self, widget, *a):
		if self.recursing: return
		self.current.is_template = widget.get_active()
		self.on_profile_modified()
	
	
	def setup_commandline(self):
		def aso(long_name, short_name, description,
				arg=GLib.OptionArg.NONE,
				flags=GLib.OptionFlags.IN_MAIN):
			""" add_simple_option, adds program argument in simple way """
			o = GLib.OptionEntry()
			if short_name:
				o.long_name = long_name
				o.short_name = short_name
			o.description = description
			o.flags = flags
			o.arg = arg
			self.add_main_option_entries([o])
		
		aso("verbose",	b"v", "Be verbose")
		aso("debug",	b"d", "Be more verbose (debug mode)")
		aso("osd",		b"o", "OSD mode (displays only editor only)")
		self.connect('handle-local-options', self.do_local_options)
	
	
	def save_profile_selection(self, path):
		""" Saves name of profile into config file """
		name = os.path.split(path)[-1]
		if name.endswith(".sccprofile"):
			name = name[0:-11]
		
		data = dict(current_profile=name)
		jstr = json.dumps(data, sort_keys=True, indent=4)
		
		open(os.path.join(get_config_path(), self.CONFIG), "w").write(jstr)
	
	
	def load_profile_selection(self):
		""" Returns name profile from config file or None if there is none saved """
		try:
			return self.config['recent_profiles'][0]
		except:
			return None
	
	
	@staticmethod
	def get_release(n=3):
		"""
		Returns current version rounded to max. 'n' numbers.
		( v0.14.1.3 ; n=3 -> v0.14.1 )
		"""
		return ".".join(DAEMON_VERSION.split(".")[0:n])
	
	
	def release_notes_visible(self):
		""" Returns True if release notes infobox is visible """
		if not self.ribar: return False
		riNewRelease = self.builder.get_object('riNewRelease')
		return self.ribar._infobar == riNewRelease
	
	
	def check_release_notes(self):
		"""
		Silently downloads release notes from github and displays infobar
		informing user that they are ready to be displayed.
		"""
		url = App.RELEASE_URL % (App.get_release(),)
		log.debug("Loading release notes from '%s'", url)
		f = Gio.File.new_for_uri(url)
		buffer = b""
		
		def stream_ready(stream, task, buffer):
			try:
				bytes = stream.read_bytes_finish(task)
				if bytes.get_size() > 0:
					buffer += bytes.get_data()
					stream.read_bytes_async(102400, 0, None, stream_ready, buffer)
				else:
					self.on_got_release_notes(buffer.decode("utf-8"))
			except Exception, e:
				log.warning("Failed to read release notes")
				log.exception(e)
				return
		
		def http_ready(f, task, buffer):
			try:
				stream = f.read_finish(task)
				assert stream
				stream.read_bytes_async(102400, 0, None, stream_ready, buffer)
			except Exception, e:
				log.warning("Failed to read release notes")
				log.exception(e)
				log.warning("(above error is not fatal and can be ignored)")
				return
		
		f.read_async(0, None, http_ready, buffer)
	
	
	def on_got_release_notes(self, data):
		"""" Called after entire HTML page of release notes is downloaded """
		# There is actually only one thing parsed here;
		# Sequence of words "see ... for more", in bold, containing <A> tag.
		# If such sequence is found, it's displayed with message about extended
		# release notes. Otherwise, shorter text and link to github is used.
		RE_EXTENDED = r'<strong>see.*href=\"([^\"]+).*for more.*</strong>'
		
		if self.ribar is not None:
			# There is already some error displayed, don't bother now...
			return
		
		msg = ""
		extended = re.search(RE_EXTENDED, data, re.IGNORECASE)
		if extended:
			msg += _("<a href='%s'>Click here</a> to check what's new!")
			msg = msg % (extended.group(1), )
		else:
			url = App.RELEASE_URL % (App.get_release(), )
			msg += _("Welcome to the version <b>%s</b>.")
			msg += " " + _("<a href='%s'>Click here</a> to read release notes.")
			msg = msg % (App.get_release(), url)
		
		infobar = self.builder.get_object('riNewRelease')
		lblNewRelease = self.builder.get_object('lblNewRelease')
		lblNewRelease.set_markup(msg)
		ribar = RIBar(None, infobar=infobar)
		ribar = self.show_error(None, ribar=ribar)
		self.ribar.connect("close", self.on_new_release_dismissed)
		self.ribar.connect("response", self.on_new_release_dismissed)
		
		
	def on_new_release_dismissed(self, *a):
		self.config['gui']['news']['last_version'] = App.get_release()
		self.config.save() 
	
	
	def on_cbNewRelease_toggled(self, cb):
		self.app.config['gui']['news']['enabled'] = cb.get_active()
		self.config.save()
	
	
	def on_drag_data_received(self, widget, context, x, y, data, info, time):
		""" Drag-n-drop handler """
		uri = None
		if str(data.get_data_type()) == "text/uri-list":
			# Only file can be dropped here
			if len(data.get_uris()):
				uri = data.get_uris()[0]
		elif str(data.get_data_type()) == "text/plain":
			# This can be anything, so try to extract uri from it
			lines = str(data.get_data()).split("\n")
			if len(lines) > 0:
				first = lines[0]
				if first.startswith("http://") or first.startswith("https://") or first.startswith("ftp://"):
					# I don't like other protocols
					uri = first
		if uri:
			from scc.gui.importexport.dialog import Dialog
			giofile = None
			if uri.startswith("file://"):
				giofile = Gio.File.new_for_uri(uri)
			else:
				# Local file can be used directly, remote has to
				# be downloaded first
				if uri.startswith("https://github.com/"):
					# Convert link to repository display to link to raw file
					uri = (uri
						.replace("https://github.com/", "https://raw.githubusercontent.com/")
						.replace("/blob/", "/")
					)
				name = urllib.unquote(".".join(uri.split("/")[-1].split(".")[0:-1]))
				remote = Gio.File.new_for_uri(uri)
				tmp, stream = Gio.File.new_tmp("%s.XXXXXX" % (name,))
				stream.close()
				if remote.copy(tmp, Gio.FileCopyFlags.OVERWRITE, None, None):
					# Sucessfully downloaded
					log.info("Downloaded '%s'" % (uri,))
					giofile = tmp
				else:
					# Failed. Just do nothing
					return
			if giofile.get_path():
				path = giofile.get_path().decode("utf-8")
				filetype = Dialog.determine_type(path)
				if filetype:
					log.info("Importing '%s'..." % (filetype))
					log.debug("(type %s)" % (filetype,))
					ied = Dialog(self)
					ied.show(self.window)
					# Skip first screen and try to import this file
					ied.import_file(path, filetype = filetype)
				else:
					log.error("Unknown file type: '%s'..." % (path,))


class UndoRedo(object):
	""" Just dummy container """
	def __init__(self, id, before, after):
		self.id = id
		self.before = before
		self.after = after
