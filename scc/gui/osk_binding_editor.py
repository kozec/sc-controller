#!/usr/bin/env python2
"""
SC-Controller - On Screen Keyboard Binding Editor

Edits '.scc-osd.keyboard.sccprofile', profile used by on screen keyboard
"""
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gdk
from scc.actions import Action, ACTIONS
from scc.paths import get_profiles_path
from scc.constants import SCButtons
from scc.tools import find_profile
from scc.profile import Profile
from scc.gui.binding_editor import BindingEditor
from scc.gui.parser import GuiActionParser
from scc.gui.editor import Editor
from scc.osd.keyboard_actions import OSK

import os, logging
log = logging.getLogger("OSKEdit")


class OSKBindingEditor(Editor, BindingEditor):
	GLADE = "osk_binding_editor.glade"
	OSK_PROF_NAME = ".scc-osd.keyboard"
	
	def __init__(self, app):
		BindingEditor.__init__(self)
		self.app = app
		self.gladepath = app.gladepath
		self.imagepath = app.imagepath
		ACTIONS['OSK'] = OSK
		self.current = Profile(GuiActionParser())
		self.current.load(find_profile(OSKBindingEditor.OSK_PROF_NAME))
		self.setup_widgets()
	
	
	def setup_widgets(self):
		Editor.setup_widgets(self)
		self.create_binding_buttons(use_icons=False)
	
	
	def show_editor(self, id, press=False):
		if id in SCButtons:
			title = _("%s Button") % (id.name,)
			if press:
				title = _("%s Press") % (id.name,)
			ae = self.choose_editor(self.current.buttons[id], title)
			ae.set_button(id, self.current.buttons[id], mode=Action.AC_OSK)
			ae.hide_modifiers()
			# ae.hide_osd()
			ae.show(self.window)
		pass
	
	
	def on_action_chosen(self, id, action, reopen=False):
		self.set_action(self.current, id, action)
		if reopen:
			self.show_editor(id)
		else:
			self.save_profile()
	
	
	def save_profile(self, *a):
		"""
		Saves osk profile from 'profile' object into 'giofile'.
		Calls on_profile_saved when done
		"""
		self.current.save(os.path.join(get_profiles_path(),
				OSKBindingEditor.OSK_PROF_NAME + ".sccprofile"))
		# OSK reloads profile when daemon reports configuration change
		self.app.dm.reconfigure()
