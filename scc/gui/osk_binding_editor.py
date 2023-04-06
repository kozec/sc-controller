#!/usr/bin/env python2
"""
SC-Controller - On Screen Keyboard Binding Editor

Edits '.scc-osd.keyboard.sccprofile', profile used by on screen keyboard
"""

from scc.tools import _

from gi.repository import Gdk
from scc.constants import SCButtons, STICK
from scc.paths import get_profiles_path
from scc.tools import find_profile
from scc.profile import Profile
from scc.actions import Action
from scc.gui.binding_editor import BindingEditor
from scc.gui.controller_widget import TRIGGERS, STICKS
from scc.gui.parser import GuiActionParser
from scc.gui.editor import Editor
from scc.osd.keyboard import Keyboard as OSDKeyboard

import os, logging
log = logging.getLogger("OSKEdit")


class OSKBindingEditor(Editor, BindingEditor):
	GLADE = "osk_binding_editor.glade"
	
	def __init__(self, app):
		BindingEditor.__init__(self, app)
		self.app = app
		self.gladepath = app.gladepath
		self.imagepath = app.imagepath
		self.current = Profile(GuiActionParser())
		self.current.load(find_profile(OSDKeyboard.OSK_PROF_NAME))
		self.setup_widgets()
	
	
	def setup_widgets(self):
		Editor.setup_widgets(self)
		self.create_binding_buttons(use_icons=False, enable_press=False)
	
	
	def show_editor(self, id):
		if id in STICKS:
			ae = self.choose_editor(self.current.stick,
				_("Stick"))
			ae.set_input(STICK, self.current.stick, mode=Action.AC_OSK)
			ae.show(self.window)
		elif id in SCButtons:
			title = _("%s Button") % (id.name,)
			ae = self.choose_editor(self.current.buttons[id], title)
			ae.set_input(id, self.current.buttons[id], mode=Action.AC_OSK)
			ae.show(self.window)
		elif id in TRIGGERS:
			ae = self.choose_editor(self.current.triggers[id],
				_("%s Trigger") % (id,))
			ae.set_input(id, self.current.triggers[id], mode=Action.AC_OSK)
			ae.show(self.window)
	
	
	def on_action_chosen(self, id, action, mark_changed=True):
		self.set_action(self.current, id, action)
		self.save_profile()
	
	
	def save_profile(self, *a):
		"""
		Saves osk profile from 'profile' object into 'giofile'.
		Calls on_profile_saved when done
		"""
		self.current.save(os.path.join(get_profiles_path(),
				OSDKeyboard.OSK_PROF_NAME + ".sccprofile"))
		# OSK reloads profile when daemon reports configuration change
		self.app.dm.reconfigure()
