#!/usr/bin/env python2
"""
SC-Controller - Action Editor

Allows to edit button or trigger action.
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.gui.controller_widget import ControllerButton
from scc.gui.editor import Editor
from scc.actions import SleepAction, PressAction, ReleaseAction
from scc.actions import Action, ButtonAction, NoAction
from scc.actions import Macro, Repeat, Cycle
from scc.constants import SCButtons
from scc.profile import Profile

from gi.repository import Gtk, Gdk, GLib
from collections import namedtuple
import os, logging
log = logging.getLogger("MacroEditor")

class MacroEditor(Editor):
	GLADE = "macro_editor.glade"
	
	def __init__(self, app, callback):
		Editor.__init__(self)
		self.app = app
		self.id = None
		self.mode = Action.AC_BUTTON
		self.ac_callback = callback
		self.added_widget = None
		self.setup_widgets()
		self.actions = []
	
	
	def update_action_field(self):
		""" Updates field on bottom """
		entAction = self.builder.get_object("entAction")
		cbMacroType = self.builder.get_object("cbMacroType")
		btAddDelay = self.builder.get_object("btAddDelay")
		entAction.set_text(self._make_action().to_string())
		
		# Disable all action type comboboxes in Cycle mode,
		# only click is allowed there;
		# Reenable them if action type is set to anything else.
		sens = cbMacroType.get_active() != 2
		for ad in self.actions:
			if isinstance(ad.action, ButtonAction) or isinstance(ad.action, PressAction):
				if sens:
					ad.combo.set_sensitive(True)
				else:
					ad.combo.set_active(0)
					ad.combo.set_sensitive(False)
			elif isinstance(ad.action, SleepAction):
				ad.label.set_sensitive(sens)
				ad.scale.set_sensitive(sens)
		# Do same thing for 'Add Delay' button
		btAddDelay.set_sensitive(sens)
	
	
	def _make_action(self):
		""" Generates and returns Action instance """
		entName = self.builder.get_object("entName")
		cbMacroType = self.builder.get_object("cbMacroType")
		pars = [ x[0] for x in self.actions ]
		if len(pars) == 0:
			# No action is actually set
			action = NoAction()
		elif cbMacroType.get_active() == 2:
			# Cycle
			pars = filter(lambda a : not isinstance(a, SleepAction), pars)
			action = Cycle(*pars)
		elif cbMacroType.get_active() == 1:
			# Repeating macro
			action = Macro(*pars)
			action.repeat = True
		elif len(pars) == 1:
			# Only one action
			action = pars[0]
		else:
			# Macro
			action = Macro(*pars)
		if entName.get_text().decode("utf-8").strip() != "":
			action.name = entName.get_text().decode("utf-8").strip()
		return action
	
	
	def _add_action(self, action):
		""" Adds widgets for new action """
		grActions = self.builder.get_object("grActions")
		model = self.builder.get_object("lstPressClickOrHold")
		i = len(self.actions) + 1
		action.name = None
		action_data = None
		
		# Buttons
		button_up, button_down, button_clear = Gtk.Button(), Gtk.Button(), Gtk.Button()
		b = Gtk.Button.new_with_label(action.describe(self.mode))
		
		# Action button
		b.set_property("hexpand", True)
		b.set_property("margin-left", 10)
		b.set_property("margin-right", 10)
		
		if isinstance(action, ButtonAction) or isinstance(action, PressAction):
			# Combobox
			c = Gtk.ComboBox()
			c.set_model(model)
			c.set_size_request(100, -1)
			renderer = Gtk.CellRendererText()
			c.pack_start(renderer, True)
			c.add_attribute(renderer, 'text', 1)
			if isinstance(action, ReleaseAction):
				c.set_active(2)
				b.set_label(action.describe_short())
			elif isinstance(action, PressAction):
				c.set_active(1)
				b.set_label(action.describe_short())
			else:
				c.set_active(0)
			action_data = ActionData( action = action, button_up = button_up,
				button_down = button_down, button_clear = button_clear,
				combo = c, button_action = b)
			
			c.connect('changed', self.on_buttonaction_type_change, i - 1, action_data)
			grActions.attach(c,			0, i, 1, 1)
			grActions.attach(b,			1, i, 1, 1)
		elif isinstance(action, SleepAction):
			# Label and scale
			l = Gtk.Label("")
			l.set_xalign(0.0)
			l.set_size_request(100, -1)
			s = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 5, 5000, 5)
			s.set_draw_value(False)
			s.set_value(action.delay * 1000)
			action_data = ActionData( action = action, button_up = button_up,
				button_down = button_down, button_clear = button_clear,
				label = l, scale = s)
			
			s.connect('change_value', self.on_change_delay, action_data)
			grActions.attach(l,			0, i, 1, 1)
			grActions.attach(s,			1, i, 1, 1)
			self.on_change_delay(s, None, action.delay * 1000, action_data)
		else:
			# Placeholder
			l = Gtk.Label("")
			l.set_size_request(100, -1)
			
			action_data = ActionData( action = action, button_up = button_up,
				button_down = button_down, button_clear = button_clear,
				label = l, button_action = b)
			
			grActions.attach(l,			0, i, 1, 1)
			grActions.attach(b,			1, i, 1, 1)
		
		b.connect('clicked',			self.on_actionb_clicked, i - 1, action_data)
		button_clear.connect('clicked',	self.on_clearb_clicked, action_data)
		button_up.connect('clicked',	self.on_moveb_clicked, -1, action_data)
		button_down.connect('clicked',	self.on_moveb_clicked,  1, action_data)
		
		# Move Up button
		button_up.set_image(Gtk.Image.new_from_stock("gtk-go-up", Gtk.IconSize.SMALL_TOOLBAR))
		button_up.set_relief(Gtk.ReliefStyle.NONE)
		
		# Move Down button
		button_down.set_image(Gtk.Image.new_from_stock("gtk-go-down", Gtk.IconSize.SMALL_TOOLBAR))
		button_down.set_relief(Gtk.ReliefStyle.NONE)
		
		# Clear button
		button_clear.set_image(Gtk.Image.new_from_stock("gtk-delete", Gtk.IconSize.SMALL_TOOLBAR))
		button_clear.set_relief(Gtk.ReliefStyle.NONE)
		
		# Pack
		grActions.attach(button_up,		2, i, 1, 1)
		grActions.attach(button_down,	3, i, 1, 1)
		grActions.attach(button_clear,	4, i, 1, 1)
		
		# Disable 'up' button on 1st aciton
		if len(self.actions) == 0:
			button_up.set_sensitive(False)
		# Reenable 'down' button on last action
		if len(self.actions) > 0:
			self.actions[-1].button_down.set_sensitive(True)
		# Disable 'down' on added (now last) action
		button_down.set_sensitive(False)
		
		self.actions.append(action_data)
		self.update_action_field()
		grActions.show_all()
	
	
	def on_moveb_clicked(self, trash, direction, action_data):
		""" Handler for 'move action' buttons """
		action = action_data.action
		readd = [ x.action for x in self.actions ]
		index = readd.index(action) + direction
		if index < 0:
			# Not possible to move 1st item up
			return
		if index > len(readd):
			# Not possible to move last item down
			return
		readd.remove(action)
		readd.insert(index, action)
		self._refill_grid(readd)
		self.update_action_field()
	
	
	def on_clearb_clicked(self, trash, action_data):
		""" Handler for 'delete action' button """
		self._clear_grid()
		self.actions.remove(action_data)
		readd = [ x.action for x in self.actions ]
		self._refill_grid(readd)
		self.update_action_field()
	
	
	def on_cbMacroType_changed(self, *a):
		self.update_action_field()
	
	
	def on_buttonaction_type_change(self, cb, i, action_data):
		action = action_data.action
		if isinstance(action, (PressAction, ReleaseAction)):
			action = action.action
		if cb.get_active() == 0:
			if isinstance(action, ButtonAction):
				self.actions[i] = action_data._replace(action = ButtonAction(action.button))
		elif cb.get_active() == 1:
			self.actions[i] = action_data._replace(action = PressAction(action))
		else:
			self.actions[i] = action_data._replace(action = ReleaseAction(action))
		self.update_action_field()
		
	
	def _clear_grid(self):
		""" Removes everything from UI """
		grActions = self.builder.get_object("grActions")
		for child in [] + grActions.get_children():
			grActions.remove(child)
	
	
	def _refill_grid(self, new_actions):
		""" Removes everything from UI and then adds updated stuff back """
		self._clear_grid()
		self.actions = []
		for a in new_actions:
			self._add_action(a)
	
	
	def on_change_delay(self, scale, trash, value, action_data):
		""" Called when delay slider is moved """
		ms = int(value)
		action = action_data.action
		label = action_data.label
		action.delay = value / 1000.0
		if ms < 1000:
			label.set_markup(_("<b>Delay: %sms</b>") % (ms,))
		else:
			s = ms / 1000.0
			label.set_markup(_("<b>Delay: %0.2fs</b>") % (s,))
		self.update_action_field()
	
	
	def on_actionb_clicked(self, button, i, action_data):
		""" Handler clicking on action name """
		def on_chosen(id, action):
			readd = [ x.action for x in self.actions ]
			readd[i] = action
			self._refill_grid(readd)
			self.update_action_field()
		
		from scc.gui.action_editor import ActionEditor	# Cannot be imported @ top
		ae = ActionEditor(self.app, on_chosen)
		ae.set_title(_("Edit Action"))
		ae.set_input(self.id, action_data.action, mode=self.mode)
		ae.hide_modeshift()
		ae.hide_macro()
		ae.hide_name()
		ae.show(self.window)
	
	
	def on_btAddAction_clicked(self, *a):
		""" Handler for Add Action button """
		self._add_action(NoAction())
	
	
	def on_btAddDelay_clicked(self, *a):
		""" Handler for Add Delay button """
		self._add_action(SleepAction(0.5))
	
	
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
	
	
	def on_btOK_clicked(self, *a):
		""" Handler for OK button """
		a = self._make_action()
		if self.ac_callback is not None:
			self.ac_callback(self.id, a)
		self.close()
	
	
	def add_widget(self, label, widget):
		"""
		See ActionEditor.add_widget
		"""
		lblAddedWidget = self.builder.get_object("lblAddedWidget")
		vbAddedWidget = self.builder.get_object("vbAddedWidget")
		lblAddedWidget.set_label(label)
		lblAddedWidget.set_visible(True)
		for ch in vbAddedWidget.get_children():
			vbAddedWidget.remove(ch)
		self.added_widget = widget
		vbAddedWidget.pack_start(widget, True, False, 0)
		vbAddedWidget.set_visible(True)
	
	
	def on_Dialog_destroy(self, *a):
		vbAddedWidget = self.builder.get_object("vbAddedWidget")
		for ch in vbAddedWidget.get_children():
			vbAddedWidget.remove(ch)	
	
	
	def allow_first_page(self):
		""" For compatibility with action editor. Does nothing """
		pass
	
	
	def set_input(self, id, action, mode=Action.AC_BUTTON):
		""" Common part of editor setup """
		btDefault = self.builder.get_object("btDefault")
		entName = self.builder.get_object("entName")
		cbMacroType = self.builder.get_object("cbMacroType")
		self.id = id
		self.mode = mode
		self.set_title("Macro for %s" % (id.name if id in SCButtons else str(id),))
		if isinstance(action, Cycle):
			cbMacroType.set_active(2)
		elif action.repeat:
			cbMacroType.set_active(1)
		else:
			cbMacroType.set_active(0)
		for a in action.actions:
			self._add_action(a)
		if action.name is not None:
			entName.set_text(action.name)
	
	
	def hide_name(self):
		"""
		Hides (and clears) name field.
		"""
		self.builder.get_object("lblName").set_visible(False)
		self.builder.get_object("entName").set_visible(False)
		self.builder.get_object("entName").set_text("")


ActionData = namedtuple('ActionData',
	'action, button_up, button_down, button_clear, button_action,'
	'combo, label, scale')
ActionData.__new__.__defaults__ = (None,) * len(ActionData._fields)
