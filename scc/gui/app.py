#!/usr/bin/env python2
"""
SC-Controller - App

Main application window
"""
from __future__ import unicode_literals
from scc.tools import _, set_logging_level

from gi.repository import Gtk, Gio, GLib
from scc.gui.controller_widget import TRIGGERS, PADS, STICKS, GYROS, BUTTONS, PRESSABLE
from scc.gui.controller_widget import ControllerPad, ControllerStick, ControllerGyro
from scc.gui.controller_widget import ControllerButton, ControllerTrigger
from scc.gui.modeshift_editor import ModeshiftEditor
from scc.gui.profile_manager import ProfileManager
from scc.gui.ae.gyro_action import is_gyro_enable
from scc.gui.daemon_manager import DaemonManager
from scc.gui.action_editor import ActionEditor
from scc.gui.macro_editor import MacroEditor
from scc.gui.parser import GuiActionParser
from scc.gui.svg_widget import SVGWidget
from scc.gui.dwsnc import headerbar
from scc.gui.ribar import RIBar
from scc.paths import get_daemon_path, get_config_path, get_profiles_path
from scc.modifiers import ModeModifier, SensitivityModifier
from scc.actions import XYAction, NoAction
from scc.macros import Macro, Repeat
from scc.constants import SCButtons
from scc.profile import Profile

import os, sys, json, logging
log = logging.getLogger("App")

class App(Gtk.Application, ProfileManager):
	"""
	Main application / window.
	"""
	
	IMAGE = "background.svg"
	HILIGHT_COLOR = "#FF00FF00"		# ARGB
	CONFIG = "scc.config.json"
	
	def __init__(self, gladepath="/usr/share/scc",
						imagepath="/usr/share/scc/images"):
		Gtk.Application.__init__(self,
				application_id="me.kozec.scc",
				flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)
		ProfileManager.__init__(self)
		# Setup Gtk.Application
		self.setup_commandline()
		# Setup DaemonManager
		self.dm = DaemonManager()
		self.dm.connect("alive", self.on_daemon_alive)
		self.dm.connect("profile-changed", self.on_daemon_profile_changed)
		self.dm.connect("error", self.on_daemon_error)
		self.dm.connect("dead", self.on_daemon_dead)
		# Set variables
		self.gladepath = gladepath
		self.imagepath = imagepath
		self.builder = None
		self.recursing = False
		self.daemon_changed_profile = False
		self.background = None
		self.current = Profile(GuiActionParser())
		self.current_file = None
		self.just_started = True
		self.button_widgets = {}
		self.undo = []
		self.redo = []
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.gladepath, "app.glade"))
		self.builder.connect_signals(self)
		self.window = self.builder.get_object("window")
		self.add_window(self.window)
		self.window.set_title(_("SC Controller"))
		self.window.set_wmclass("SC Controller", "SC Controller")
		self.ribar = None
		
		for b in BUTTONS:
			self.button_widgets[b] = ControllerButton(self, b, self.builder.get_object("bt" + b.name))
		for b in TRIGGERS:
			self.button_widgets[b] = ControllerTrigger(self, b, self.builder.get_object("btTrigger" + b))
		for b in PADS:
			self.button_widgets[b] = ControllerPad(self, b, self.builder.get_object("bt" + b))
		for b in STICKS:
			self.button_widgets[b] = ControllerStick(self, b, self.builder.get_object("bt" + b))
		for b in GYROS:
			self.button_widgets[b] = ControllerGyro(self, b, self.builder.get_object("bt" + b))
		
		self.builder.get_object("cbProfile").set_row_separator_func(
			lambda model, iter : model.get_value(iter, 1) is None and model.get_value(iter, 0) == "-" )
		
		self.set_daemon_status("unknown")
		
		vbc = self.builder.get_object("vbC")
		main_area = self.builder.get_object("mainArea")
		vbc.get_parent().remove(vbc)
		vbc.connect('size-allocate', self.on_vbc_allocated)
		self.background = SVGWidget(self, os.path.join(self.imagepath, self.IMAGE))
		self.background.connect('hover', self.on_background_area_hover)
		self.background.connect('leave', self.on_background_area_hover, None)
		self.background.connect('click', self.on_background_area_click)
		main_area.put(self.background, 0, 0)
		main_area.put(vbc, 0, 0) # (self.IMAGE_SIZE[0] / 2) - 90, self.IMAGE_SIZE[1] - 100)
		headerbar(self.builder.get_object("hbWindow"))
	
	
	def check(self):
		""" Performs various (two) checks and reports possible problems """
		# TODO: Maybe not best place to do this
		if os.path.exists("/dev/uinput"):
			if not os.access("/dev/uinput", os.R_OK | os.W_OK):
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
		self.background.hilight({ button : App.HILIGHT_COLOR })
	
	
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
	
	
	def _choose_editor(self, action, title):
		if isinstance(action, SensitivityModifier):
			action = action.action
		if isinstance(action, ModeModifier) and not is_gyro_enable(action):
			e = ModeshiftEditor(self, self.on_action_chosen)
			e.set_title(_("Mode Shift for %s") % (title,))
		elif isinstance(action, Macro):
			e = MacroEditor(self, self.on_action_chosen)
			e.set_title(_("Macro for %s") % (title,))
		else:
			e = ActionEditor(self, self.on_action_chosen)
			e.set_title(title)
		return e
		
	
	def show_editor(self, id, press=False):
		if id in SCButtons:
			title = _("%s Button") % (id.name,)
			if press:
				title = _("%s Press") % (id.name,)
			ae = self._choose_editor(self.current.buttons[id], title)
			ae.set_button(id, self.current.buttons[id])
			ae.show(self.window)
		elif id in TRIGGERS:
			ae = self._choose_editor(self.current.triggers[id],
				_("%s Trigger") % (id,))
			ae.set_trigger(id, self.current.triggers[id])
			ae.show(self.window)
		elif id in STICKS:
			ae = self._choose_editor(self.current.stick,
				_("Stick"))
			ae.set_stick(self.current.stick)
			ae.show(self.window)
		elif id in GYROS:
			ae = self._choose_editor(self.current.gyro,
				_("Gyro"))
			ae.set_gyro(self.current.gyro)
			ae.show(self.window)
		elif id in PADS:
			data = NoAction()
			if id == "LPAD":
				data = self.current.pads[Profile.LEFT]
				ae = self._choose_editor(data, _("Left Pad"))
			else:
				data = self.current.pads[Profile.RIGHT]
				ae = self._choose_editor(data, _("Right Pad"))
			ae.set_pad(id, data)
			ae.show(self.window)
	
	
	def on_btUndo_clicked(self, *a):
		if len(self.undo) < 1: return
		undo, self.undo = self.undo[-1], self.undo[0:-1]
		self._set_action(undo.id, undo.before)
		self.redo.append(undo)
		self.builder.get_object("btRedo").set_sensitive(True)
		if len(self.undo) < 1:
			self.builder.get_object("btUndo").set_sensitive(False)
		self.on_profile_changed()
	
	
	def on_btRedo_clicked(self, *a):
		if len(self.redo) < 1: return
		redo, self.redo = self.redo[-1], self.redo[0:-1]
		self._set_action(redo.id, redo.after)
		self.undo.append(redo)
		self.builder.get_object("btUndo").set_sensitive(True)
		if len(self.redo) < 1:
			self.builder.get_object("btRedo").set_sensitive(False)
		self.on_profile_changed()
	
	
	def on_profiles_loaded(self, profiles):
		cb = self.builder.get_object("cbProfile")
		model = cb.get_model()
		model.clear()
		i = 0
		current_profile, current_index = self.load_profile_selection(), 0
		for f in profiles:
			name = f.get_basename()
			if name.endswith(".mod"):
				continue
			if name.endswith(".sccprofile"):
				name = name[0:-11]
			if name == current_profile:
				current_index = i
			model.append((name, f, None))
			i += 1
		model.append(("-", None, None))
		model.append((_("New profile..."), None, None))
		
		if cb.get_active_iter() is None:
			cb.set_active(current_index)
	
	
	def on_cbProfile_changed(self, cb, *a):
		""" Called when user chooses profile in selection combo """
		if self.recursing : return
		model = cb.get_model()
		iter = cb.get_active_iter()
		f = model.get_value(iter, 1)
		if f is None:
			if self.current_file is None:
				cb.set_active(0)
			else:
				self.select_profile(self.current_file.get_path())
			
			new_name = os.path.split(self.current_file.get_path())[-1]
			if new_name.endswith(".mod"): new_name = new_name[0:-4]
			if new_name.endswith(".sccprofile"): new_name = new_name[0:-11]
			new_name = _("Copy of") + " " + new_name
			dlg = self.builder.get_object("dlgNewProfile")
			txNewProfile = self.builder.get_object("txNewProfile")
			txNewProfile.set_text(new_name)
			dlg.set_transient_for(self.window)
			dlg.show()
		else:
			self.load_profile(f)
			if not self.daemon_changed_profile:
				self.dm.set_profile(f.get_path())
			self.save_profile_selection(f.get_path())
	
	
	def on_dlgNewProfile_delete_event(self, dlg, *a):
		dlg.hide()
		return True
	
	
	def on_btNewProfile_clicked(self, *a):
		""" Called when new profile name is set and OK is clicked """
		txNewProfile = self.builder.get_object("txNewProfile")
		dlg = self.builder.get_object("dlgNewProfile")
		cb = self.builder.get_object("cbProfile")
		name = txNewProfile.get_text()
		filename = txNewProfile.get_text() + ".sccprofile"
		path = os.path.join(get_profiles_path(), filename)
		self.current_file = Gio.File.new_for_path(path)
		self.recursing = True
		model = cb.get_model()
		model.insert(0, ( name, self.current_file, None ))
		cb.set_active(0)
		self.recursing = False
		self.save_profile(self.current_file, self.current)
		dlg.hide()
	
	
	def on_profile_loaded(self, profile, giofile):
		self.current = profile
		self.current_file = giofile
		for b in self.button_widgets.values():
			b.update()
		self.on_profile_saved(giofile, False)	# Just to indicate that there are no changes to save
	
	
	def on_profile_changed(self, *a):
		"""
		Called when selected profile is modified in memory.
		Displays "changed" next to profile name and shows Save button.
		
		If sccdaemon is alive, creates 'original.filename.mod' and loads it
		into daemon to activate changes right away.
		"""
		cb = self.builder.get_object("cbProfile")
		self.builder.get_object("rvProfileChanged").set_reveal_child(True)
		model = cb.get_model()
		for row in model:
			if self.current_file == model.get_value(row.iter, 1):
				model.set_value(row.iter, 2, _("(changed)"))
				break
		
		if self.dm.is_alive():
			modfile = Gio.File.new_for_path(self.current_file.get_path() + ".mod")
			self.save_profile(modfile, self.current)
	
	
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
		
		cb = self.builder.get_object("cbProfile")
		self.builder.get_object("rvProfileChanged").set_reveal_child(False)
		model = cb.get_model()
		for row in model:
			if model.get_value(row.iter, 1) == self.current_file:
				model.set_value(row.iter, 1, giofile)
			model.set_value(row.iter, 2, None)
		
		if send and self.dm.is_alive() and not self.daemon_changed_profile:
			self.dm.set_profile(giofile.get_path())
		
		self.current_file = giofile
	
	
	def on_btSaveProfile_clicked(self, *a):
		self.save_profile(self.current_file, self.current)
	
	
	def on_action_chosen(self, id, action, reopen=False):
		before = self._set_action(id, action)
		if type(before) != type(action) or before.to_string() != action.to_string():
			# TODO: Maybe better comparison
			self.undo.append(UndoRedo(id, before, action))
			self.builder.get_object("btUndo").set_sensitive(True)
		self.on_profile_changed()
		if reopen:
			self.show_editor(id)
	
	
	def _set_action(self, id, action):
		"""
		Stores action in profile.
		Returns formely stored action.
		"""
		before = NoAction()
		if id in BUTTONS:
			before, self.current.buttons[id] = self.current.buttons[id], action
			self.button_widgets[id].update()
		if id in PRESSABLE:
			before, self.current.buttons[id] = self.current.buttons[id], action
			self.button_widgets[id.name].update()
		elif id in TRIGGERS:
			before, self.current.triggers[id] = self.current.triggers[id], action
			self.button_widgets[id].update()
		elif id in GYROS:
			before, self.current.gyro = self.current.gyro, action
			self.button_widgets[id].update()
		elif id in STICKS + PADS:
			if id in STICKS:
				before, self.current.stick = self.current.stick, action
			elif id == "LPAD":
				before, self.current.pads[Profile.LEFT] = self.current.pads[Profile.LEFT], action
			else:
				before, self.current.pads[Profile.RIGHT] = self.current.pads[Profile.RIGHT], action
			self.button_widgets[id].update()
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
	
	
	def on_mnuExit_activate(self, *a):
		self.quit()
	
	
	def on_daemon_alive(self, *a):
		self.set_daemon_status("alive")
		self.hide_error()
		if self.current_file is not None and not self.just_started:
			self.dm.set_profile(self.current_file.get_path())
	
	
	def on_daemon_error(self, trash, error):
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
		self.set_daemon_status("dead")
	
	
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
	
	
	def on_daemon_profile_changed(self, trash, profile):
		current_changed = self.builder.get_object("rvProfileChanged").get_reveal_child()
		if profile.endswith(".mod"):
			try:
				os.unlink(profile)
			except Exception, e:
				log.warning("Failed to remove .mod file")
				log.warning(e)
		if self.just_started or not current_changed:
			log.debug("Daemon uses profile '%s', selecting it in UI", profile)
			self.daemon_changed_profile = True
			found = self.select_profile(profile)
			self.daemon_changed_profile = False
			if not found:
				# Daemon uses unknown profile, override it with something I know about
				if self.current_file is not None:
					self.dm.set_profile(self.current_file.get_path())
				
		self.just_started = False
	
	
	def on_daemon_dead(self, *a):
		if self.just_started:
			self.dm.restart()
			self.just_started = False
			self.set_daemon_status("unknown")
			return
		self.set_daemon_status("dead")
	
	
	def on_mnuEmulationEnabled_toggled(self, cb):
		if self.recursing : return
		if cb.get_active():
			# Turning daemon on
			self.set_daemon_status("unknown")
			cb.set_sensitive(False)
			self.dm.start()
		else:
			# Turning daemon off
			self.set_daemon_status("unknown")
			cb.set_sensitive(False)
			self.dm.stop()
			
	
	def do_startup(self, *a):
		Gtk.Application.do_startup(self, *a)
		self.load_profile_list()
		self.setup_widgets()
		GLib.timeout_add_seconds(2, self.check)
	
	
	def do_local_options(self, trash, lo):
		set_logging_level(lo.contains("verbose"), lo.contains("debug") )
		return -1
	
	
	def do_command_line(self, cl):
		Gtk.Application.do_command_line(self, cl)
		self.activate()
		return 0
	
	
	def do_activate(self, *a):
		self.builder.get_object("window").show()
	
	
	def select_profile(self, name):
		"""
		Selects profile in profile selection combobox.
		Returns True on success or False if profile is not in combobox.
		"""
		if name.endswith(".mod"): name = name[0:-4]
		if name.endswith(".sccprofile"): name = name[0:-11]
		if "/" in name : name = os.path.split(name)[-1]
		
		cb = self.builder.get_object("cbProfile")
		model = cb.get_model()
		active = cb.get_active_iter()
		for row in model:
			if model.get_value(row.iter, 1) is not None:
				if name == model.get_value(row.iter, 0):
					if active == row.iter:
						# Already selected
						return True
					cb.set_active_iter(row.iter)
					return True
		return False
	
	
	def set_daemon_status(self, status):
		""" Updates image that shows daemon status and menu shown when image is clicked """
		log.debug("daemon status: %s", status)
		icon = os.path.join(self.imagepath, "status_%s.svg" % (status,))
		imgDaemonStatus = self.builder.get_object("imgDaemonStatus")
		btDaemon = self.builder.get_object("btDaemon")
		mnuEmulationEnabled = self.builder.get_object("mnuEmulationEnabled")
		imgDaemonStatus.set_from_file(icon)
		mnuEmulationEnabled.set_sensitive(True)
		self.window.set_icon_from_file(icon)
		self.recursing = True
		if status == "alive":
			btDaemon.set_tooltip_text(_("Emulation is active"))
			mnuEmulationEnabled.set_active(True)
		elif status == "dead":
			btDaemon.set_tooltip_text(_("Emulation is inactive"))
			mnuEmulationEnabled.set_active(False)
		else:
			btDaemon.set_tooltip_text(_("Checking emulation status..."))
		self.recursing = False
	
	
	def setup_commandline(self):
		def aso(long_name, short_name, description,
				arg=GLib.OptionArg.NONE,
				flags=GLib.OptionFlags.IN_MAIN):
			""" add_simple_option, adds program argument in simple way """
			o = GLib.OptionEntry()
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


class UndoRedo(object):
	""" Just dummy container """
	def __init__(self, id, before, after):
		self.id = id
		self.before = before
		self.after = after
