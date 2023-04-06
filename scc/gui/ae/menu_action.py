#!/usr/bin/env python2
"""
SC-Controller - Action Editor - common part of "DPAD or menu" and "Special Action",
two components with MenuAction selectable.
"""

from scc.tools import _

from gi.repository import Gtk
from scc.special_actions import MenuAction, HorizontalMenuAction
from scc.special_actions import RadialMenuAction, GridMenuAction
from scc.special_actions import QuickMenuAction, PositionModifier
from scc.constants import SCButtons, SAME, STICK, DEFAULT
from scc.paths import get_menus_path
from scc.actions import NoAction
from scc.tools import nameof
from scc.gui.userdata_manager import UserDataManager
from scc.gui.menu_editor import MenuEditor
from scc.gui.parser import GuiActionParser

import os, logging
log = logging.getLogger("AE.Menu")

__all__ = [ 'MenuActionCofC' ]


class MenuActionCofC(UserDataManager):
	# CofC - Component of Component
	def __init__(self):
		UserDataManager.__init__(self)
		self._current_menu = None
		self.parser = GuiActionParser()
		self.allow_globals = True
		self.allow_in_profile = True
	
	
	def allow_menus(self, allow_globals, allow_in_profile):
		"""
		Sets which type of menu should be selectable.
		By default, both are enabled.
		
		Returns self.
		"""
		self.allow_globals = allow_globals
		self.allow_in_profile = allow_in_profile
		return self
	
	
	def set_selected_menu(self, menu):
		"""
		Sets menu selected in combobox.
		Returns self.
		"""
		self._current_menu = menu
		# TODO: This currently works only if menu list is not yet loaded
	
	
	@staticmethod
	def menu_class_to_key(action):
		"""
		For subclass of MenuAction, returns correct key to be used in ListStore.
		"""
		if isinstance(action, GridMenuAction):
			return "gridmenu"
		elif isinstance(action, QuickMenuAction):
			return "quickmenu"
		elif isinstance(action, HorizontalMenuAction):
			return "hmenu"
		elif isinstance(action, RadialMenuAction):
			return "radialmenu"
		else:
			return "menu"
	
	
	def load_menu_data(self, action):
		if isinstance(action, PositionModifier):
			# Load menu position modifier, if used
			x, y = action.position
			self.builder.get_object("cbMenuPosX").set_active(0 if x >= 0 else 1)
			self.builder.get_object("cbMenuPosY").set_active(0 if y >= 0 else 1)
			self.builder.get_object("spMenuPosX").set_value(abs(x))
			self.builder.get_object("spMenuPosY").set_value(abs(y))
			action = action.action
		
		self._current_menu = action.menu_id
		cbm = self.builder.get_object("cbMenuType")
		self.set_cb(cbm, self.menu_class_to_key(action), 1)
		
		if self.builder.get_object("rvMenuSize"):
			spMenuSize = self.builder.get_object("spMenuSize")
			if self.update_size_display(action):
				size = spMenuSize.get_adjustment().set_value(action.size)
		
		cbControlWith = self.builder.get_object("cbControlWith")
		cbConfirmWith = self.builder.get_object("cbConfirmWith")
		cbCancelWith = self.builder.get_object("cbCancelWith")
		cbMenuAutoConfirm = self.builder.get_object("cbMenuAutoConfirm")
		cbMenuConfirmWithClick = self.builder.get_object("cbMenuConfirmWithClick")
		cbMenuAutoCancel = self.builder.get_object("cbMenuAutoCancel")
		if cbControlWith:
			self.set_cb(cbControlWith, nameof(action.control_with), 1)
		
		cow = action.confirm_with
		caw = action.cancel_with
		
		if cbConfirmWith:
			if cow == SAME and cbMenuAutoConfirm:
				cbMenuAutoConfirm.set_active(True)
				cbConfirmWith.set_sensitive(False)
			elif cbMenuConfirmWithClick and cow == self.get_default_confirm():
				cbMenuConfirmWithClick.set_active(True)
				cbConfirmWith.set_sensitive(False)
			else:
				if cbMenuAutoConfirm:
					cbMenuAutoConfirm.set_active(False)
				if cbMenuConfirmWithClick:
					cbMenuAutoConfirm.set_active(False)
				cbConfirmWith.set_sensitive(True)
				self.set_cb(cbConfirmWith, nameof(cow), 1)
		
		if cbCancelWith:
			if caw == SAME and cbMenuAutoCancel:
				cbMenuAutoCancel.set_active(True)
				cbCancelWith.set_sensitive(False)
			else:
				if cbMenuAutoCancel:
					cbMenuAutoCancel.set_active(False)
				self.set_cb(cbCancelWith, nameof(caw), 1)
		
		self.on_cbMenus_changed()
	
	
	def get_default_confirm(self):
		"""
		Returns DEFAULT, but may be overriden when default
		confirm button is different - specifically when used with pads.
		"""
		return DEFAULT
	
	
	def get_default_cancel(self):
		"""
		Returns DEFAULT, but may be overriden when default
		confirm button is different - specifically when used with pads.
		"""
		return DEFAULT
	
	
	def on_menu_changed(self, new_id):
		self._current_menu = new_id
		self.editor.set_action(MenuAction(new_id))
		self.load_menu_list()
	
	
	def on_btEditMenu_clicked(self, *a):
		name = self.get_selected_menu()
		if name:
			log.debug("Editing %s", name)
			me = MenuEditor(self.app, self.on_menu_changed)
			id = self.get_selected_menu()
			log.debug("Opening editor for menu ID '%s'", id)
			me.set_menu(id)
			me.allow_menus(self.allow_globals, self.allow_in_profile)
			me.show(self.editor.window)
	
	
	def on_cbMenus_button_press_event(self, trash, event):
		if event.button == 3:
			mnuMenu = self.builder.get_object("mnuMenu")
			mnuMenu.popup(None, None, None, None,
				3, Gtk.get_current_event_time())
	
	
	def on_mnuMenuNew_activate(self, *a):
		self.on_new_menu_selected()
	
	
	def on_mnuMenuCopy_activate(self, *a):
		self.on_new_menu_selected(make_copy=True)
	
	
	def on_mnuMenuRename_activate(self, *a):
		self.on_btEditMenu_clicked()
	
	
	def on_mnuMenuDelete_activate(self, *a):
		id = self.get_selected_menu()
		if MenuEditor.menu_is_global(id):
			text = _("Really delete selected global menu?")
		else:
			text = _("Really delete selected menu?")
		
		d = Gtk.MessageDialog(parent=self.editor.window,
			flags = Gtk.DialogFlags.MODAL,
			type = Gtk.MessageType.WARNING,
			buttons = Gtk.ButtonsType.OK_CANCEL,
			message_format = text,
		)
		
		if MenuEditor.menu_is_global(id):
			d.format_secondary_text(_("This action is not undoable!"))
		
		if d.run() == -5: # OK button, no idea where is this defined...
			if MenuEditor.menu_is_global(id):
				fname = os.path.join(get_menus_path(), id)
				try:
					os.unlink(fname)
				except Exception as e:
					log.error("Failed to remove %s: %s", fname, e)
			else:
				del self.app.current.menus[id]
				self.app.on_profile_modified()
			self.load_menu_list()
		d.destroy()
	
	
	def on_menus_loaded(self, menus):
		cb = self.builder.get_object("cbMenus")
		cb.set_row_separator_func( lambda model, iter : model.get_value(iter, 1) is None )
		model = cb.get_model()
		model.clear()
		i, current_index = 0, 0
		if self.allow_in_profile:
			# Add menus from profile
			for key in sorted(self.app.current.menus):
				model.append((key, key))
				if self._current_menu == key:
					current_index = i
				i += 1
			if i > 0:
				model.append((None, None))	# Separator
				i += 1
		if self.allow_globals:
			for f in menus:
				key = f.get_basename()
				name = key
				if name.startswith("."): continue
				if "." in name:
					name = _("%s (global)" % (name.split(".")[0]))
				model.append((name, key))
				if self._current_menu == key:
					current_index = i
				i += 1
		if i > 0:
			model.append((None, None))	# Separator
		model.append(( _("New Menu..."), "" ))
		
		self._recursing = True
		cb.set_active(current_index)
		self._recursing = False
		name = self.get_selected_menu()
		if name:
			self.builder.get_object("btEditMenu").set_sensitive(name not in MenuEditor.OPEN)
	
	
	def handles(self, mode, action):
		if isinstance(action, PositionModifier):
			return isinstance(action.action, MenuAction)
		return isinstance(action, MenuAction)
	
	
	def get_selected_menu(self):
		cb = self.builder.get_object("cbMenus")
		model = cb.get_model()
		iter = cb.get_active_iter()
		if iter is None:
			# Empty list
			return None
		return model.get_value(iter, 1)
	
	
	def prevent_confirm_cancel_nonsense(self, widget, *a):
		"""
		If 'confirm with click', 'confirm with release' and
		'cbMenuAutoCancel' are all present, this method prevents them from
		being checked in nonsensical way.
		"""
		cbMenuConfirmWithClick = self.builder.get_object("cbMenuConfirmWithClick")
		cbMenuAutoConfirm = self.builder.get_object("cbMenuAutoConfirm")
		cbMenuAutoCancel = self.builder.get_object("cbMenuAutoCancel")
		if widget.get_active():
			if widget == cbMenuConfirmWithClick:
				if cbMenuAutoConfirm:
					cbMenuAutoConfirm.set_active(False)
			elif widget == cbMenuAutoConfirm:
				if cbMenuConfirmWithClick:
					cbMenuConfirmWithClick.set_active(False)
				if cbMenuAutoCancel:
					cbMenuAutoCancel.set_active(False)
			elif widget == cbMenuAutoCancel:
				if cbMenuAutoConfirm:
					cbMenuAutoConfirm.set_active(False)
	
	
	def on_cbMenus_changed(self, *a):
		""" Called when user changes any menu settings """
		if self._recursing : return
		cbMenuConfirmWithClick = self.builder.get_object("cbMenuConfirmWithClick")
		cbMenuAutoConfirm = self.builder.get_object("cbMenuAutoConfirm")
		cbMenuAutoCancel = self.builder.get_object("cbMenuAutoCancel")
		lblControlWith = self.builder.get_object("lblControlWith")
		cbControlWith = self.builder.get_object("cbControlWith")
		lblConfirmWith = self.builder.get_object("lblConfirmWith")
		cbConfirmWith = self.builder.get_object("cbConfirmWith")
		lblCancelWith = self.builder.get_object("lblCancelWith")
		cbCancelWith = self.builder.get_object("cbCancelWith")
		
		cbm = self.builder.get_object("cbMenuType")
		menu_type = cbm.get_model().get_value(cbm.get_active_iter(), 1)
		
		if cbControlWith:
			sensitive = True
			if menu_type == "quickmenu":
				sensitive = False
			lblControlWith.set_sensitive(sensitive)
			cbControlWith.set_sensitive(sensitive)
		
		if cbConfirmWith:
			sensitive = True
			if cbMenuAutoConfirm and cbMenuAutoConfirm.get_active():
				sensitive = False
			if cbMenuConfirmWithClick and cbMenuConfirmWithClick.get_active():
				sensitive = False
			if menu_type == "quickmenu":
				sensitive = False
			lblConfirmWith.set_sensitive(sensitive)
			cbConfirmWith.set_sensitive(sensitive)
		
		if cbCancelWith:
			sensitive = True
			if cbMenuAutoCancel and cbMenuAutoCancel.get_active():
				sensitive = False
			if menu_type == "quickmenu":
				sensitive = False
			lblCancelWith.set_sensitive(sensitive)
			cbCancelWith.set_sensitive(sensitive)
		
		if cbMenuAutoConfirm:
			sensitive = True
			if menu_type == "quickmenu":
				sensitive = False
			cbMenuAutoConfirm.set_sensitive(sensitive)
		
		name = self.get_selected_menu()
		if name == "":
			return self.on_new_menu_selected()
		if name:
			# There is some menu choosen
			self.builder.get_object("btEditMenu").set_sensitive(name not in MenuEditor.OPEN)
			params = [ name ]
			
			cow = SAME
			if cbMenuAutoConfirm and cbMenuAutoConfirm.get_active():
				cow = SAME
			elif cbMenuConfirmWithClick and cbMenuConfirmWithClick.get_active():
				cow = DEFAULT
			elif cbConfirmWith:
				cow = cbConfirmWith.get_model().get_value(cbConfirmWith.get_active_iter(), 1)
				if cow != DEFAULT:
					cow = getattr(SCButtons, cow)
			
			caw = DEFAULT
			if cbMenuAutoCancel and cbMenuAutoCancel.get_active():
				caw = DEFAULT
			elif cbCancelWith:
				caw = cbCancelWith.get_model().get_value(cbCancelWith.get_active_iter(), 1)
				if caw != DEFAULT:
					caw = getattr(SCButtons, caw)
			
			params += [ self.get_control_with(), cow, caw ]
			
			
			# Hide / apply and display 'Items per row' selector if it exists in UI
			if self.builder.get_object("rvMenuSize"):
				spMenuSize = self.builder.get_object("spMenuSize")
				menu_type = cbm.get_model().get_value(cbm.get_active_iter(), 1)
				if menu_type == "gridmenu":
					self.update_size_display(GridMenuAction("dummy"))
					size = int(spMenuSize.get_adjustment().get_value())
					if size > 0:
						# size is 2nd parameter
						params += [ False, size ]
				elif menu_type == "radialmenu":
					self.update_size_display(RadialMenuAction("dummy"))
					size = int(spMenuSize.get_adjustment().get_value())
					if size > 0 and size < 100:
						# Both 0 and 100 means default here
						# size is 2nd parameter
						params += [ False, size ]
				elif menu_type == "hmenu":
					self.update_size_display(HorizontalMenuAction("dummy"))
					size = int(spMenuSize.get_adjustment().get_value())
					if size > 1:
						# Size 0 and 1 means default here
						# size is 2nd parameter
						params += [ False, size ]
				else:
					# , "radialmenu"):
					self.update_size_display(None)
			
			# Grab menu type and choose apropriate action
			action = NoAction()
			if cbm and menu_type == "gridmenu":
				# Grid menu
				action = GridMenuAction(*params)
			elif cbm and menu_type == "radialmenu":
				# Circular menu
				action = RadialMenuAction(*params)
			elif cbm and menu_type == "hmenu":
				# Horizontal menu
				action = HorizontalMenuAction(*params)
			elif cbm and menu_type == "quickmenu":
				# Horizontal menu
				action = QuickMenuAction(name)
			else:
				# Normal menu
				action = MenuAction(*params)
			
			# Apply Menu Position options, if such block exists in UI
			if self.builder.get_object("spMenuPosX"):
				cbMenuPosX = self.builder.get_object("cbMenuPosX")
				cbMenuPosY = self.builder.get_object("cbMenuPosY")
				x = int(self.builder.get_object("spMenuPosX").get_value())
				y = int(self.builder.get_object("spMenuPosY").get_value())
				x *= cbMenuPosX.get_model().get_value(cbMenuPosX.get_active_iter(), 0)
				y *= cbMenuPosY.get_model().get_value(cbMenuPosY.get_active_iter(), 0)
				if (x, y) != MenuAction.DEFAULT_POSITION:
					action = PositionModifier(x, y, action)
			
			self.editor.set_action(action)
	
	
	def on_new_menu_selected(self, make_copy=False):
		# 'New menu' selected
		self.load_menu_list()
		log.debug("Creating editor for new menu")
		me = MenuEditor(self.app, self.on_menu_changed)
		if make_copy:
			name = self.get_selected_menu()
			log.debug("Copying %s", name)
			me = MenuEditor(self.app, self.on_menu_changed)
			me.set_menu(name)
		me.set_new_menu()
		me.allow_menus(self.allow_globals, self.allow_in_profile)
		me.show(self.editor.window)
	
	
	def update_size_display(self, action):
		"""
		Displays or hides menu size area and upadates text displayed in it.
		Returns True if action is menuaction where changing size makes sense
		"""
		rvMenuSize = self.builder.get_object("rvMenuSize")
		lblMenuSize = self.builder.get_object("lblMenuSize")
		spMenuSize = self.builder.get_object("spMenuSize")
		sclMenuSize = self.builder.get_object("sclMenuSize")
		if isinstance(action, GridMenuAction):
			spMenuSize.set_visible(True)
			sclMenuSize.set_visible(False)
			lblMenuSize.set_text(_("Items per row"))
			rvMenuSize.set_reveal_child(True)
			return True
		elif isinstance(action, (RadialMenuAction, HorizontalMenuAction)):
			spMenuSize.set_visible(False)
			sclMenuSize.set_visible(True)
			lblMenuSize.set_text(_("Size"))
			rvMenuSize.set_reveal_child(True)
			return True
		else:
			rvMenuSize.set_reveal_child(False)
			return False	
	
	
	def get_control_with(self):
		""" Returns value of "Control With" combo or STICK if there is none """
		cbControlWith = self.builder.get_object("cbControlWith")
		if cbControlWith:
			return cbControlWith.get_model().get_value(cbControlWith.get_active_iter(), 1)
		return STICK
	
	
	def on_spMenuSize_format_value(self, spinner):
		val = int(spinner.get_adjustment().get_value())
		if val < 1:
			spinner.get_buffer().set_text(_("auto"), -1)
		else:
			spinner.get_buffer().set_text(str(val), -1)
		return True
	
	
	def on_sclMenuSize_format_value(self, scale, val):
		cbm = self.builder.get_object("cbMenuType")
		menu_type = cbm.get_model().get_value(cbm.get_active_iter(), 1)
		if menu_type == "radialmenu":
			if val < 1:
				return _("default")
			return  "%s%%" % (int(val),)
		else: # if menu_type == "hmenu"
			val = int(val)
			if val < 2:
				return _("default")
			return str(int(val))
