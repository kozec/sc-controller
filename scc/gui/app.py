#!/usr/bin/env python2
"""
SC-Controller - App

Main application window
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gdk, Gio, GLib
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
from scc.paths import get_config_path, get_profiles_path
from scc.tools import check_access, find_profile
from scc.actions import NoAction
from scc.modifiers import NameModifier
from scc.profile import Profile
from scc.config import Config

import scc.osd.menu_generators
import os, sys, json, logging
log = logging.getLogger("App")

class App(Gtk.Application, UserDataManager, BindingEditor):
	"""
	Main application / window.
	"""
	
	IMAGE = "background.svg"
	HILIGHT_COLOR = "#FF00FF00"		# ARGB
	OBSERVE_COLOR = "#00007FFF"		# ARGB
	CONFIG = "scc.config.json"
	
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
			Gtk.TargetEntry.new("text/uri-list", Gtk.TargetFlags.OTHER_APP, 0)
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
		
		# Headerbar
		headerbar(self.builder.get_object("hbWindow"))
	
	
	def setup_statusicon(self):
		menu = self.builder.get_object("mnuDaemon")
		self.statusicon = get_status_icon(self.imagepath, menu)
		self.statusicon.connect('clicked', self.on_statusicon_clicked)
		GLib.idle_add(self.statusicon.set, "scc-%s" % (self.status,), _("SC-Controller"))
	
	
	def destroy_statusicon(self):
		self.statusicon.destroy()
		self.statusicon = None
	
	
	def check(self):
		""" Performs various (two) checks and reports possible problems """
		# TODO: Maybe not best place to do this
		if os.path.exists("/dev/uinput"):
			if not check_access("/dev/uinput"):
				# Cannot acces uinput
				msg = _('You don\'t have required access to /dev/uinput.')
				msg += "\n" + _('This will most likely prevent emulation from working.')
				msg += "\n\n" + _('Please, consult your distribution manual on how to enable uinput')
				self.show_error(msg)
		else:
			# There is no uinput
			msg = _('/dev/uinput not found')
			msg += "\n" + _('Your kernel is either outdated or compiled without uinput support.')
			msg += "\n\n" + _('Please, consult your distribution manual on how to enable uinput')
			self.show_error(msg)
	
	
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
		ae = self.choose_editor(action, "")
		ae.set_input(id, action)
		ae.show(self.window)
	
	
	def show_context_menu(self, for_id):
		""" Sets sensitivity of popup menu items and displays it on screen """
		mnuPopup = self.builder.get_object("mnuPopup")
		mnuCopy = self.builder.get_object("mnuCopy")
		mnuClear = self.builder.get_object("mnuClear")
		mnuPaste = self.builder.get_object("mnuPaste")
		self.context_menu_for = for_id
		clp = Gtk.Clipboard.get_default(Gdk.Display.get_default())
		mnuCopy.set_sensitive(bool(self.get_action(self.current, for_id)))
		mnuClear.set_sensitive(bool(self.get_action(self.current, for_id)))
		mnuPaste.set_sensitive(clp.wait_is_text_available())
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
			return True
		return False # Allow
	
	
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
		
	
	def on_mnuGlobalSettings_activate(self, *a):
		from scc.gui.global_settings import GlobalSettings
		gs = GlobalSettings(self)
		gs.show(self.window)
	
	
	def on_mnuImport_activate(self, *a):
		"""
		Handler for 'Import Steam Profile' context menu item.
		Displays apropriate dialog.
		"""
		from scc.gui.import_dialog import ImportDialog
		gs = ImportDialog(self)
		gs.show(self.window)
	
	
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
	
	
	def on_dlgNewProfile_delete_event(self, dlg, *a):
		dlg.hide()
		return True
	
	
	def on_btNewProfile_clicked(self, *a):
		""" Called when new profile name is set and OK is clicked """
		txNewProfile = self.builder.get_object("txNewProfile")
		dlg = self.builder.get_object("dlgNewProfile")
		self.new_profile(self.current, txNewProfile.get_text())
		dlg.hide()
	
	
	def on_profile_modified(self, *a):
		"""
		Called when selected profile is modified in memory.
		"""
		self.profile_switchers[0].set_profile_modified(True)
		
		if not self.current_file.get_path().endswith(".mod"):
			mod = self.current_file.get_path() + ".mod"
			self.current_file = Gio.File.new_for_path(mod)
		
		self.save_profile(self.current_file, self.current)
	
	
	def on_profile_loaded(self, profile, giofile):
		self.current = profile
		self.current_file = giofile
		self.profile_switchers[0].set_profile_modified(False)
		for b in self.button_widgets.values():
			b.update()
	
	
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
		
		self.save_profile(self.current_file, self.current)
	
	
	def on_profile_saved(self, giofile, send=True):
		"""
		Called when selected profile is saved to disk
		"""
		if giofile.get_path().endswith(".mod"):
			# Special case, this one is saved only to be sent to daemon
			# and user doesn't need to know about it
			if self.dm.is_alive():
				self.dm.set_profile(giofile.get_path())
			return
		
		self.profile_switchers[0].set_profile_modified(False)
		if send and self.dm.is_alive() and not self.daemon_changed_profile:
			self.dm.set_profile(giofile.get_path())
		
		self.current_file = giofile	
	
	
	def on_new_clicked(self, ps, name):
		new_name = _("Copy of %s") % (name,)
		filename = os.path.join(get_profiles_path(), new_name + ".sccprofile")
		i = 0
		while os.path.exists(filename):
			i += 1
			new_name = _("Copy of %s (%s)") % (name, i)
			filename = os.path.join(get_profiles_path(), new_name + ".sccprofile")
		
		dlg = self.builder.get_object("dlgNewProfile")
		txNewProfile = self.builder.get_object("txNewProfile")
		txNewProfile.set_text(new_name)
		dlg.set_transient_for(self.window)
		dlg.show()
	
	
	def on_action_chosen(self, id, action):
		before = self.set_action(self.current, id, action)
		if before.to_string() != action.to_string():
			# TODO: Maybe better comparison
			self.undo.append(UndoRedo(id, before, action))
			self.builder.get_object("btUndo").set_sensitive(True)
		self.on_profile_modified()
	
	
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
	
	
	def on_mnuExit_activate(self, *a):
		self.quit()
	
	
	def on_mnuAbout_activate(self, *a):
		from scc.gui.aboutdialog import AboutDialog
		AboutDialog(self).show(self.window)
	
	
	def on_daemon_alive(self, *a):
		self.set_daemon_status("alive", True)
		self.hide_error()
		self.just_started = False
		if self.profile_switchers[0].get_file() is not None and not self.just_started:
			self.dm.set_profile(self.current_file.get_path())
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
				self.profile_switchers.append(s)
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
	
	
	def add_switcher(self, margin_left=20, margin_right=40, margin_bottom=2):
		"""
		Adds new profile switcher widgets on top of window. Called
		when new controller is connected to daemon.
		
		Returns generated ProfileSwitcher instance.
		"""
		vbAllProfiles = self.builder.get_object("vbAllProfiles")
		
		ps = ProfileSwitcher(self)
		ps.set_margin_left(margin_left)
		ps.set_margin_right(margin_right)
		ps.set_margin_bottom(margin_bottom)
		
		vbAllProfiles.pack_start(ps, False, False, 0)
		vbAllProfiles.reorder_child(ps, 0)
		vbAllProfiles.show_all()
		
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
	
	
	def enable_test_mode(self):
		"""
		Disables and re-enables Input Test mode. If sniffing is disabled in
		daemon configuration, 2nd call fails and logs error.
		"""
		if self.dm.is_alive():
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
		
		self.show_error(msg)
		self.set_daemon_status("error", True)
	
	
	def on_daemon_event_observer(self, daemon, what, data):
		if what in (LEFT, RIGHT, STICK):
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
			if data[0]:
				self.hilights[App.OBSERVE_COLOR].add(what)
			else:
				self.hilights[App.OBSERVE_COLOR].remove(what)
			self._update_background()
		else:
			print "event", what
	
	
	def show_error(self, message):
		if self.ribar is None:
			self.ribar = RIBar(message, Gtk.MessageType.ERROR)
			content = self.builder.get_object("content")
			content.pack_start(self.ribar, False, False, 1)
			content.reorder_child(self.ribar, 0)
			self.ribar.connect("close", self.hide_error)
			self.ribar.connect("response", self.hide_error)
		else:
			self.ribar.get_label().set_markup(message)
		self.ribar.show()
		self.ribar.set_reveal_child(True)
	
	
	def hide_error(self, *a):
		if self.ribar is not None:
			if self.ribar.get_parent() is not None:
				self.ribar.get_parent().remove(self.ribar)
		self.ribar = None
	
	
	def on_daemon_reconfigured(self, *a):
		log.debug("Reloading config...")
		self.config.reload()
	
	
	def on_daemon_dead(self, *a):
		if self.just_started:
			self.dm.restart()
			self.just_started = False
			self.set_daemon_status("unknown", True)
			return
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
		GLib.timeout_add_seconds(2, self.check)
	
	
	def do_local_options(self, trash, lo):
		set_logging_level(lo.contains("verbose"), lo.contains("debug") )
		return -1
	
	
	def do_command_line(self, cl):
		Gtk.Application.do_command_line(self, cl)
		if len(cl.get_arguments()) > 1:
			filename = cl.get_arguments()[-1]
			giofile = Gio.File.new_for_path(filename)
			# Local file, looks like vdf profile
			from scc.gui.import_dialog import ImportDialog
			gs = ImportDialog(self)
			def i_told_you_to_quit(*a):
				sys.exit(0)
			gs.window.connect('destroy', i_told_you_to_quit)
			gs.show(self.window)
			# Skip first screen and try to import this file
			gs.on_preload_finished(gs.set_file, giofile.get_path())
		else:
			self.activate()
		return 0
	
	
	def do_activate(self, *a):
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
	
	
	def set_daemon_status(self, status, daemon_runs):
		""" Updates image that shows daemon status and menu shown when image is clicked """
		log.debug("daemon status: %s", status)
		icon = os.path.join(self.imagepath, "scc-%s.svg" % (status,))
		imgDaemonStatus = self.builder.get_object("imgDaemonStatus")
		btDaemon = self.builder.get_object("btDaemon")
		mnuEmulationEnabled = self.builder.get_object("mnuEmulationEnabled")
		imgDaemonStatus.set_from_file(icon)
		mnuEmulationEnabled.set_sensitive(True)
		self.window.set_icon_from_file(icon)
		self.status = status
		if self.statusicon:
			GLib.idle_add(self.statusicon.set, "scc-%s" % (self.status,), _("SC-Controller"))
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
		self.recursing = False
	
	
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
		
		self.connect('handle-local-options', self.do_local_options)
		
		aso("verbose",	b"v", "Be verbose")
		aso("debug",	b"d", "Be more verbose (debug mode)")
	
	
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
			data = json.loads(open(os.path.join(get_config_path(), self.CONFIG), "r").read())
			return data['current_profile']
		except:
			return None
	
	
	def on_drag_data_received(self, widget, context, x, y, data, info, time):
		""" Drag-n-drop handler """
		if str(data.get_data_type()) == "text/uri-list":
			# Only file can be dropped here
			if len(data.get_uris()):
				uri = data.get_uris()[0]
				giofile = Gio.File.new_for_uri(uri)
				if giofile.get_path():
					path = giofile.get_path()
					if path.endswith(".vdf") or path.endswith(".vdffz"):
						# Local file, looks like vdf profile
						from scc.gui.import_dialog import ImportDialog
						gs = ImportDialog(self)
						gs.show(self.window)
						# Skip first screen and try to import this file
						gs.on_preload_finished(gs.set_file, giofile.get_path())


class UndoRedo(object):
	""" Just dummy container """
	def __init__(self, id, before, after):
		self.id = id
		self.before = before
		self.after = after
