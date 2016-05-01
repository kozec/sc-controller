#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.gui.controller_widget import ControllerButton
from scc.gui.editor import Editor
from scc.constants import SCButtons
from scc.gui.dwsnc import headerbar
from scc.actions import Action, NoAction
from scc.modifiers import ModeModifier
from scc.profile import Profile
from scc.macros import Macro

from gi.repository import Gtk, Gdk, GLib
import os, logging
log = logging.getLogger("ModeshiftEditor")

class ModeshiftEditor(Editor):
	GLADE = "modeshift_editor.glade"
	BUTTONS = (	# in order as displayed in combobox
		(SCButtons.A,			_('A') ),
		(SCButtons.B,			_('B') ),
		(SCButtons.X,			_('X') ),
		(SCButtons.Y,			_('Y') ),
		(None, None),
		(SCButtons.BACK,		_('Back (select)') ),
		(SCButtons.C,			_('Center') ),
		(SCButtons.START,		_('Start') ),
		(None, None),
		(SCButtons.LGRIP,		_('Left Grip') ),
		(SCButtons.RGRIP,		_('Right Grip') ),
		(None, None),
		(SCButtons.LB,			_('Left Bumper') ),
		(SCButtons.RB,			_('Right Bumper') ),
		(SCButtons.LT,			_('Left Trigger') ),
		(SCButtons.RT,			_('Right Trigger') ),
		(None, None),
		(SCButtons.LPAD,		_('Left Pad Pressed') ),
		(SCButtons.RPAD,		_('Right Pad Pressed') ),
		(SCButtons.LPADTOUCH,	_('Left Pad Touched') ),
		(SCButtons.RPADTOUCH,	_('Right Pad Touched</') ),
	)
	
	def __init__(self, app, callback):
		self.app = app
		self.id = None
		self.mode = Action.AC_BUTTON
		self.ac_callback = callback
		self.setup_widgets()
		self.actions = []
		self.default = NoAction()
	
	
	def setup_widgets(self):
		self.builder = Gtk.Builder()
		self.builder.add_from_file(os.path.join(self.app.gladepath, self.GLADE))
		self.window = self.builder.get_object("Dialog")
		self.builder.connect_signals(self)
		
		cbButtonChooser = self.builder.get_object("cbButtonChooser")
		cbButtonChooser.set_row_separator_func( lambda model, iter : model.get_value(iter, 0) is None )
		model = cbButtonChooser.get_model()
		for button, text in self.BUTTONS:
			model.append(( None if button is None else button.name, text ))
		cbButtonChooser.set_active(0)
		headerbar(self.builder.get_object("header"))
	
	
	def _add_action(self, button, action):
		grActions = self.builder.get_object("grActions")
		cbButtonChooser = self.builder.get_object("cbButtonChooser")
		model = cbButtonChooser.get_model()
		
		for row in model:
			if model.get_value(row.iter, 0) == button.name:
				model.remove(row.iter)
				break
		try:
			while model.get_value(model[0].iter, 0) is None:
				model.remove(model[0].iter)
			cbButtonChooser.set_active(0)
		except: pass
		
		i = len(self.actions) + 1
		l = Gtk.Label()
		l.set_markup("<b>%s</b>" % (button.name,))
		l.set_xalign(0.0)
		b = Gtk.Button.new_with_label(action.describe(self.mode))
		b.set_property("hexpand", True)
		b.connect('clicked', self.on_actionb_clicked, button)
		clearb = Gtk.Button()
		clearb.set_image(Gtk.Image.new_from_stock("gtk-delete", Gtk.IconSize.SMALL_TOOLBAR))
		clearb.set_relief(Gtk.ReliefStyle.NONE)
		clearb.connect('clicked', self.on_clearb_clicked, button)
		grActions.attach(l,			0, i, 1, 1)
		grActions.attach(b,			1, i, 1, 1)
		grActions.attach(clearb,	2, i, 1, 1)
		
		self.actions.append([ button, action, l, b, clearb ])
		grActions.show_all()
	
	
	def on_clearb_clicked(self, trash, button):
		grActions = self.builder.get_object("grActions")
		cbButtonChooser = self.builder.get_object("cbButtonChooser")
		model = cbButtonChooser.get_model()
		# Remove requested action from the list
		for i in xrange(0, len(self.actions)):
			if self.actions[i][0] == button:
				button, action, l, b, clearb = self.actions[i]
				for w in (l, b, clearb): grActions.remove(w)
				del self.actions[i]
				break
		# Move everything after that action one position up
		# - remove it
		for j in xrange(i, len(self.actions)):
			button, action, l, b, clearb = self.actions[j]
			for w in (l, b, clearb): grActions.remove(w)
		# - add it again
		for j in xrange(i, len(self.actions)):
			button, action, l, b, clearb = self.actions[j]
			grActions.attach(l,			0, j + 1, 1, 1)
			grActions.attach(b,			1, j + 1, 1, 1)
			grActions.attach(clearb,	2, j + 1, 1, 1)
		# Regenereate combobox with removed button added back to it
		# - Store acive item from in combobox
		active, i, index = None, 0, -1
		try:
			active = model.get_value(cbButtonChooser.get_active_iter(), 0)
		except: pass
		# Clear entire combobox
		model.clear()
		# Fill it again
		for button, text in self.BUTTONS:
			model.append(( None if button is None else button.name, text ))
			if button is not None:
				if button.name == active:
					index = i
			i += 1
		# Reselect formely active item
		if index >= 0:
			cbButtonChooser.set_active(index)
	
	
	def _setup_editor(self, ae, action):
		if self.mode == Action.AC_BUTTON:
			ae.set_button(self.id, action)
		elif self.mode == Action.AC_TRIGGER:
			ae.set_trigger(self.id, action)
		elif self.mode == Action.AC_STICK:
			ae.set_stick(action)
		elif self.mode == Action.AC_PAD:
			ae.set_pad(self.id, action)		
	
	
	def _choose_editor(self, action, cb):
		if isinstance(action, Macro):
			from scc.gui.macro_editor import MacroEditor	# Cannot be imported @ top
			e = MacroEditor(self.app, cb)
			e.set_title(_("Edit Macro"))
		else:
			from scc.gui.action_editor import ActionEditor	# Cannot be imported @ top
			e = ActionEditor(self.app, cb)
			e.set_title(_("Edit Action"))
			e.hide_modeshift()
		return e

	
	def on_actionb_clicked(self, trash, clicked_button):
		for i in self.actions:
			button, action, l, b, clearb = i
			if button == clicked_button:
				def on_chosen(id, action, reopen=False):
					b.set_label(action.describe(self.mode))
					i[1] = action
					if reopen: self.on_actionb_clicked(trash, clicked_button)
				
				ae = self._choose_editor(action, on_chosen)
				self._setup_editor(ae, action)
				ae.show(self.window)
				return
	
	
	def on_btDefault_clicked(self, *a):
		btDefault = self.builder.get_object("btDefault")
		def on_chosen(id, action, reopen=False):
			btDefault.set_label(action.describe(self.mode))
			self.default = action
			if reopen: self.on_btDefault_clicked()
		
		ae = self._choose_editor(self.default, on_chosen)
		self._setup_editor(ae, self.default)
		ae.show(self.window)
	
	
	def on_btClearDefault_clicked(self, *a):
		self.default = NoAction()
		btDefault = self.builder.get_object("btDefault")
		btDefault.set_label(self.default.describe(self.mode))
	
	
	def on_btAddAction_clicked(self, *a):
		cbButtonChooser = self.builder.get_object("cbButtonChooser")
		b = getattr(SCButtons, cbButtonChooser.get_model().get_value(cbButtonChooser.get_active_iter(), 0))
		self._add_action(b, NoAction())
	
	
	def on_btClear_clicked	(self, *a):
		""" Handler for clear button """
		action = NoAction()
		if self.ac_callback is not None:
			self.ac_callback(self.id, action)
		self.close()
	
	
	def on_btOK_clicked(self, *a):
		""" Handler for OK button """
		pars = []
		for button, action, l, b, clearb in self.actions:
			pars += [ button, action ]
		if self.default:
			pars += [ self.default ]
		action = ModeModifier(*pars)
		if len(pars) == 0:
			# No action is actually set
			action = NoAction()
		elif len(pars) == 1:
			# Only default action left
			action = self.default
		if self.ac_callback is not None:
			self.ac_callback(self.id, action)
		self.close()
	
	
	def _set_mode(self, mode, id, action):
		btDefault = self.builder.get_object("btDefault")
		self.id = id
		self.mode = mode
		for key in action.mods:
			self._add_action(key, action.mods[key])
		self.default = action.default
		btDefault.set_label(self.default.describe(self.mode))
	
	
	def set_button(self, id, action):
		""" Setups editor as editor for button action """
		self._set_mode(Action.AC_BUTTON, id, action)
	
	
	def set_trigger(self, id, action):
		""" Setups editor as editor for trigger action """
		self._set_mode(Action.AC_TRIGGER, id, action)
	
	
	def set_stick(self, action):
		""" Setups action editor as editor for stick action """
		self._set_mode(Action.AC_STICK, Profile.STICK, action)
	
	
	def set_pad(self, id, action):
		""" Setups action editor as editor for pad action """
		self._set_mode(Action.AC_PAD, id, action)
