#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.gui.controller_widget import ControllerButton
from scc.gui.controller_widget import STICKS, PADS
from scc.gui.dwsnc import headerbar
from scc.gui.editor import Editor
from scc.constants import SCButtons, HapticPos, TRIGGER_MAX
from scc.actions import Action, NoAction, RangeOP, RingAction
from scc.actions import ModeModifier, DoubleclickModifier
from scc.actions import FeedbackModifier, HoldModifier
from scc.actions import Macro
from scc.profile import Profile
from scc.tools import nameof

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
		(SCButtons.LB,			_('Left Bumper') ),
		(SCButtons.RB,			_('Right Bumper') ),
		(None, None),
		(SCButtons.LT,			_('Left Trigger (full)') ),
		(SCButtons.RT,			_('Right Trigger (full)') ),
		("Soft LT",				_('Left Trigger (soft)') ),
		("Soft RT",				_('Right Trigger (soft)') ),
		(None, None),
		(SCButtons.STICKPRESS,	_('Stick Pressed') ),
		(SCButtons.LPADPRESS,	_('Left Pad Pressed') ),
		(SCButtons.RPADPRESS,	_('Right Pad Pressed') ),
		(SCButtons.LPADTOUCH,	_('Left Pad Touched') ),
		(SCButtons.RPADTOUCH,	_('Right Pad Touched') ),
	)
	
	def __init__(self, app, callback):
		Editor.__init__(self)
		self.app = app
		self.id = None
		self.mode = Action.AC_BUTTON
		self.ac_callback = callback
		self.soft_level = -1
		self.current_page = 0
		self.actions = ( [], [], [] )
		self.nomods = [ NoAction(), NoAction(), NoAction() ]
		self.setup_widgets()
	
	
	def setup_widgets(self):
		Editor.setup_widgets(self)
		
		cbButtonChooser = self.builder.get_object("cbButtonChooser")
		cbButtonChooser.set_row_separator_func( lambda model, iter : model.get_value(iter, 0) is None )
		
		b = lambda a : self.builder.get_object(a)
		self.action_widgets = (
			# Order goes: Grid, 1st Action Button, Clear Button
			# 1st group, 'pressed'
			( b('grActions'),		b('btDefault'),		b('btClearDefault') ),
			# 2nd group, 'hold'
			( b('grHold'),			b('btHold'),		b('btClearHold') ),
			# 2nd group, 'double-click'
			( b('grDoubleClick'),	b('btDoubleClick'),	b('btClearDoubleClick') ),
		)
		
		headerbar(self.builder.get_object("header"))
	
	
	def on_Dialog_destroy(self, *a):
		self.remove_added_widget()
	
	
	def _fill_button_chooser(self, *a):
		cbButtonChooser = self.builder.get_object("cbButtonChooser")
		model = cbButtonChooser.get_model()
		model.clear()
		for item, text in self.BUTTONS:
			if any([ x[0] == item for x in self.actions[self.current_page] ]):
				# Skip already added buttons
				continue
			if type(item) in (str, unicode):
				# Special case for soft pull items
				button = getattr(SCButtons, item.split(" ")[-1])
				if any([ (isinstance(x, RangeOP) and x.what == button)
							for x in self.actions[self.current_page] ]):
					# Skip already added soft pulls
					continue
			
			if item == SCButtons.STICKPRESS:
				if self.id == nameof(SCButtons.LPADPRESS):
					# Controller cannot handle pressing stick and lpad at once
					continue
			model.append(( None if item is None else nameof(item), text ))
		cbButtonChooser.set_active(0)
	
	
	def _add_action(self, index, what, action):
		cbButtonChooser = self.builder.get_object("cbButtonChooser")
		adjSoftLevel = self.builder.get_object("adjSoftLevel")
		rvSoftLevel = self.builder.get_object("rvSoftLevel")
		grActions = self.action_widgets[index][0]
		model = cbButtonChooser.get_model()
		
		for row in model:
			item = model.get_value(row.iter, 0)
			if item:
				if item == nameof(what):
					model.remove(row.iter)
					break
				if isinstance(what, RangeOP) and item.startswith("Soft"):
					if nameof(what.what) == item.split(" ")[-1]:
						model.remove(row.iter)
						break
		try:
			while model.get_value(model[0].iter, 0) is None:
				model.remove(model[0].iter)
			cbButtonChooser.set_active(0)
		except: pass
		
		i = len(self.actions[index]) + 1
		l = Gtk.Label()
		if isinstance(what, RangeOP) and what.op == ">=":
			if self.soft_level == -1:
				# First Range added, load level from it
				self.soft_level = what.value if what.value > 0.0 else 0.75
				adjSoftLevel.set_value(self.soft_level)
				rvSoftLevel.set_reveal_child(True)
				what.value = -1
			if what.value == -1:
				# Range with value taken from "Soft Pull Level" slider
				l.set_markup("<b>%s (soft pull)</b>" % (nameof(what.what),))
			else:
				# Any other range
				l.set_markup("<b>%s</b>" % (nameof(what),))
		else:
			l.set_markup("<b>%s</b>" % (nameof(what),))
		l.set_xalign(0.0)
		b = Gtk.Button.new_with_label(action.describe(self.mode))
		b.set_property("hexpand", True)
		b.connect('clicked', self.on_actionb_clicked, index, what)
		clearb = Gtk.Button()
		clearb.set_image(Gtk.Image.new_from_stock("gtk-delete", Gtk.IconSize.SMALL_TOOLBAR))
		clearb.set_relief(Gtk.ReliefStyle.NONE)
		clearb.connect('clicked', self.on_clearb_clicked, index, what)
		grActions.attach(l,			0, i, 1, 1)
		grActions.attach(b,			1, i, 1, 1)
		grActions.attach(clearb,	2, i, 1, 1)
		
		self.actions[index].append([ what, action, l, b, clearb ])
		grActions.show_all()
	
	
	def on_clearb_clicked(self, trash, index, button):
		grActions = self.action_widgets[index][0]
		cbButtonChooser = self.builder.get_object("cbButtonChooser")
		model = cbButtonChooser.get_model()
		# Remove requested action from the list
		for i in xrange(0, len(self.actions[index])):
			if self.actions[index][i][0] == button:
				button, action, l, b, clearb = self.actions[index][i]
				for w in (l, b, clearb): grActions.remove(w)
				del self.actions[index][i]
				break
		# Move everything after that action one position up
		# - remove it
		for j in xrange(i, len(self.actions[index])):
			button, action, l, b, clearb = self.actions[index][j]
			for w in (l, b, clearb): grActions.remove(w)
		# - add it again
		for j in xrange(i, len(self.actions[index])):
			button, action, l, b, clearb = self.actions[index][j]
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
			model.append(( None if button is None else nameof(button), text ))
			if button is not None:
				if nameof(button) == active:
					index = i
			i += 1
		# Reselect formely active item
		if index >= 0:
			cbButtonChooser.set_active(index)
	
	
	def _choose_editor(self, action, cb):
		from scc.gui.ring_editor import RingEditor	# Cannot be imported @ top
		if isinstance(action, Macro):
			from scc.gui.macro_editor import MacroEditor	# Cannot be imported @ top
			e = MacroEditor(self.app, cb)
			e.set_title(_("Edit Macro"))
		elif RingEditor.is_ring_action(action):
			e = RingEditor(self.app, cb)
		else:
			from scc.gui.action_editor import ActionEditor	# Cannot be imported @ top
			e = ActionEditor(self.app, cb)
			e.set_title(_("Edit Action"))
			e.hide_modeshift()
		return e
	
	
	def on_actionb_clicked(self, trash, index, clicked_button):
		for i in self.actions[index]:
			button, action, l, b, clearb = i
			if button == clicked_button:
				def on_chosen(id, action):
					b.set_label(action.describe(self.mode))
					i[1] = action
				
				ae = self._choose_editor(action, on_chosen)
				ae.set_input(self.id, action, mode = self.mode)
				ae.show(self.window)
				return
	
	
	def on_ntbMore_switch_page(self, ntb, box, index):
		self.current_page = index
		self._fill_button_chooser()
		self.builder.get_object("cbButtonChooser").set_sensitive(box.get_sensitive())
		self.builder.get_object("btAddAction").set_sensitive(box.get_sensitive())
	
	
	def on_nomodbt_clicked(self, button, *a):
		actionButton = self.action_widgets[self.current_page][1]
		
		def on_chosen(id, action):
			actionButton.set_label(action.describe(self.mode))
			self.nomods[self.current_page] = action
		
		ae = self._choose_editor(self.nomods[self.current_page], on_chosen)
		ae.set_input(self.id, self.nomods[self.current_page], mode = self.mode)
		ae.show(self.window)
	
	
	def on_nomodclear_clicked(self, button, *a):
		self.nomods[self.current_page] = NoAction()
		actionButton = self.action_widgets[self.current_page][1]
		actionButton.set_label(self.nomods[self.current_page].describe(self.mode))
	
	
	def on_btAddAction_clicked(self, *a):
		cbButtonChooser = self.builder.get_object("cbButtonChooser")
		item = cbButtonChooser.get_model().get_value(cbButtonChooser.get_active_iter(), 0)
		if item.startswith("Soft"):
			b = getattr(SCButtons, item.split(" ")[-1])
			rng = RangeOP(b, ">=", -1)
			self._add_action(self.current_page, rng, NoAction())
		else:
			b = getattr(SCButtons, item)
			self._add_action(self.current_page, b, NoAction())
	
	
	def on_sclSoftLevel_format_value(self, scale, value):
		return  "%s%%" % (int(value * 100.0),)
	
	
	def on_btClear_clicked(self, *a):
		""" Handler for clear button """
		action = NoAction()
		if self.ac_callback is not None:
			self.ac_callback(self.id, action)
		self.close()
	
	
	def on_btCustomActionEditor_clicked(self, *a):
		""" Handler for 'Custom Editor' button """
		from scc.gui.action_editor import ActionEditor	# Can't be imported on top
		e = ActionEditor(self.app, self.ac_callback)
		e.set_input(self.id, self._make_action(), mode = self.mode)
		e.hide_action_buttons()
		e.hide_advanced_settings()
		e.set_title(self.window.get_title())
		e.force_page(e.load_component("custom"), True)
		self.send_added_widget(e)
		self.close()
		e.show(self.get_transient_for())
	
	
	def on_cbHoldFeedback_toggled(self, cb, *a):
		rvHoldFeedbackAmplitude = self.builder.get_object("rvHoldFeedbackAmplitude")
		rvHoldFeedbackAmplitude.set_reveal_child(cb.get_active())
	
	
	def on_btOK_clicked(self, *a):
		""" Handler for OK button """
		if self.ac_callback is not None:
			self.ac_callback(self.id, self._make_action())
		self.close()
	
	
	def _make_action(self):
		""" Generates and returns Action instance """
		cbHoldFeedback = self.builder.get_object("cbHoldFeedback")
		sclHoldFeedback = self.builder.get_object("sclHoldFeedback")
		normalaction = self._save_modemod(0)
		holdaction = self._save_modemod(1)
		dblaction = self._save_modemod(2)
		if dblaction:
			action = DoubleclickModifier(dblaction, normalaction)
			action.holdaction = holdaction
		elif holdaction:
			action = HoldModifier(holdaction, normalaction)
		else:
			action = normalaction
		action.timeout = self.builder.get_object("adjTime").get_value()
		
		if cbHoldFeedback.get_active():
			action = FeedbackModifier(HapticPos.BOTH,
						sclHoldFeedback.get_value(), action)
		
		return action
	
	
	def _save_modemod(self, index):
		""" Generates ModeModifier from page in Notebook """
		adjSoftLevel = self.builder.get_object("adjSoftLevel")
		pars = []
		for item, action, l, b, clearb in self.actions[index]:
			if isinstance(item, RangeOP) and item.value == -1:
				# Value taken from slider
				item.value = adjSoftLevel.get_value()
			pars += [ item, action ]
		if self.nomods[index]:
			pars += [ self.nomods[index] ]
		action = ModeModifier(*pars)
		if len(pars) == 0:
			# No action is actually set
			action = NoAction()
		elif len(pars) == 1:
			# Only default action left
			action = self.nomods[index]
		return action
	
	
	def _load_modemod(self, index, action):
		for key in action.mods:
			self._add_action(index, key, action.mods[key])
	
	
	def _set_nomod_button(self, index, action):
		if isinstance(action, ModeModifier):
			self._load_modemod(index, action)
			self.nomods[index] = action.default
		else:
			self.nomods[index] = action
		actionButton = self.action_widgets[index][1]
		actionButton.set_label(self.nomods[index].describe(self.mode))
	
	
	def allow_first_page(self):
		""" For compatibility with action editor. Does nothing """
		pass
	
	
	def set_input(self, id, action, mode=None):
		btDefault = self.builder.get_object("btDefault")
		lblPressAlone = self.builder.get_object("lblPressAlone")
		cbHoldFeedback = self.builder.get_object("cbHoldFeedback")
		sclHoldFeedback = self.builder.get_object("sclHoldFeedback")
		
		self.id = id
		self._fill_button_chooser()
		
		if id in STICKS:
			lblPressAlone.set_label(_("(no button pressed)"))
			self.mode = mode = mode or Action.AC_STICK
		elif id in PADS:
			lblPressAlone.set_label(_("(no button pressed)"))
			self.mode = mode = mode or Action.AC_PAD
		else:
			lblPressAlone.set_label(_("(pressed alone)"))
			self.mode = mode = mode or Action.AC_BUTTON
		
		self.set_title("Modeshift for %s" % (nameof(id) if id in SCButtons else str(id),))
		
		if isinstance(action, FeedbackModifier):
			cbHoldFeedback.set_active(True)
			sclHoldFeedback.set_value(action.get_haptic().get_amplitude())
			action = action.action
		else:
			cbHoldFeedback.set_active(False)
			sclHoldFeedback.set_value(512)
		
		if isinstance(action, ModeModifier):
			self._load_modemod(0, action)
			self._set_nomod_button(0, action.default)
			self._set_nomod_button(1, NoAction())
			self._set_nomod_button(2, NoAction())
		elif isinstance(action, DoubleclickModifier):	# includes HoldModifier
			self._set_nomod_button(0, action.normalaction)
			self._set_nomod_button(1, action.holdaction)
			self._set_nomod_button(2, action.action)
		self.builder.get_object("adjTime").set_value(action.timeout)
		
		if mode == Action.AC_OSK:
			# This is kinda bad, but allowing Custom Editor
			# from OSK editor is in TODO
			self.builder.get_object("btCustomActionEditor").set_visible(False)
		if mode != Action.AC_BUTTON:
			for w in ("vbHold", "vbDoubleClick", "lblHold", "lblDoubleClick"):
				self.builder.get_object(w).set_sensitive(False)

