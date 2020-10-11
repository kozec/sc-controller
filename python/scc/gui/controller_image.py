#!/usr/bin/env python2
"""
SC-Controller - Controller Image

Big, SVGWidget based widget with interchangeable controller and button images.
"""
from __future__ import unicode_literals
from scc.tools import _

from scc.gui.svg_widget import SVGWidget, SVGEditor
from scc.constants import SCButtons
from scc.tools import nameof

import os, sys, copy, json, logging
log = logging.getLogger("ContImage")


class ControllerImage(SVGWidget):
	DEFAULT  = "sc"
	BUTTONS_WITH_IMAGES = (
		SCButtons.A, SCButtons.B, SCButtons.X, SCButtons.Y,
		SCButtons.BACK, SCButtons.C, SCButtons.START
	)
	
	DEFAULT_AXES = (
		# Shared between DS4 and Steam Controller
		"stick_x", "stick_y", "lpad_x", "lpad_x",
		"rpad_y", "rpad_y", "ltrig", "rtrig",
	)
	
	DEFAULT_BUTTONS = [ nameof(x) for x in BUTTONS_WITH_IMAGES ] + [
		# Used only by Steam Controller
		nameof(SCButtons.LB), nameof(SCButtons.RB),
		nameof(SCButtons.LT), nameof(SCButtons.RT),
		nameof(SCButtons.STICKPRESS),
		nameof(SCButtons.RPADPRESS),
		nameof(SCButtons.LPADPRESS),
		nameof(SCButtons.LGRIP),
		nameof(SCButtons.RGRIP),
	]
	
	
	def __init__(self, app, config=None):
		self.app = app
		self.backup = None
		self.current = self._ensure_config({})
		filename = self._make_controller_image_path(ControllerImage.DEFAULT)
		SVGWidget.__init__(self, filename)
		if config:
			self._controller_image.use_config(config)
	
	
	def _make_controller_image_path(self, img):
		return os.path.join(self.app.imagepath,
			"controller-images/%s.svg" % (img, ))
	
	
	def get_config(self):
		"""
		Returns last used config
		"""
		return self.current
	
	
	def _ensure_config(self, data):
		""" Ensure that required keys are present in config data """
		data = dict(data)
		data['gui'] = dict(data.get('gui', {}))
		data['gui']['background'] = data['gui'].get("background", "sc")
		data['gui']['buttons'] = data['gui'].get("buttons") or self._get_default_images()
		data['buttons'] = data.get("buttons") or ControllerImage.DEFAULT_BUTTONS
		data['axes'] = data.get("axes") or ControllerImage.DEFAULT_AXES
		data['gyros'] = data.get("gyros", data['gui']["background"] == "sc")
		return data
	
	
	@staticmethod
	def get_names(dict_or_tuple):
		"""
		There are three different ways how button and axis names are stored
		in config. This wrapper provides unified way to get list of them.
		"""
		if type(dict_or_tuple) in (list, tuple):
			return dict_or_tuple
		return [
			(x.get("axis", x) if hasattr(x, "get") else x)
			for x in dict_or_tuple.values()
		]
	
	
	def use_config(self, config, backup=None):
		"""
		Loads controller settings from provided config, adding default values
		when needed. Returns same config.
		"""
		self.backup = backup
		self.current = self._ensure_config(config or {})
		self.set_image(os.path.join(self.app.imagepath,
			"controller-images/%s.svg" % (self.current["gui"]["background"], )))
		self._fill_button_images(self.current["gui"]["buttons"])
		self.hilight({})
		return self.current
	
	
	def override_background(self, filename):
		"""
		Overrides background image setting. This changes config in place,
		so next time get_config is called, changed background is part of it.
		"""
		if self.backup is None:
			self.backup = copy.deepcopy(self.current)
		data = json.loads(open(os.path.join(self.app.imagepath,
			"%s.json" % (filename,)), "r").read())
		self.current["gui"]["background"] = data["gui"]["background"]
		self.use_config(self.current, self.backup)
	
	
	def override_buttons(self, filename):
		"""
		Overrides button settings. This changes config in place,
		so next time get_config is called, changed background is part of it.
		"""
		if self.backup is None:
			self.backup = copy.deepcopy(self.current)
		data = json.loads(open(os.path.join(self.app.imagepath,
			"%s.json" % (filename,)), "r").read())
		self.current["gui"]["buttons"] = data["gui"]["buttons"]
		self.current["buttons"] = data["buttons"]
		self.use_config(self.current, self.backup)
	
	
	def undo_override(self):
		""" Undoes override_* changes """
		if self.backup is not None:
			self.use_config(self.backup, None)
	
	
	def get_button_groups(self):
		groups = json.loads(open(os.path.join(self.app.imagepath,
			"button-images", "groups.json"), "r").read())
		return {
			x['key'] : x['buttons'] for x in groups
			if x['type'] == "buttons"
		}
	
	
	def _get_default_images(self):
		return self.get_button_groups()[ControllerImage.DEFAULT]
	
	
	def _fill_button_images(self, buttons):
		e = self.edit()
		SVGEditor.update_parents(e)
		target = SVGEditor.get_element(e, "controller")
		target_x, target_y = SVGEditor.get_translation(target)
		for i in xrange(len(ControllerImage.BUTTONS_WITH_IMAGES)):
			b = nameof(ControllerImage.BUTTONS_WITH_IMAGES[i])
			try:
				elm = SVGEditor.get_element(e, "AREA_%s" % (b,))
				if elm is None:
					log.warning("Area for button %s not found", b)
					continue
				x, y = SVGEditor.get_translation(elm)
				scale = 1.0
				if "scc-button-scale" in elm.attrib:
					w, h = SVGEditor.get_size(elm)
					scale = float(elm.attrib['scc-button-scale'])
					tw, th = w * scale, h * scale
					if scale < 1.0:
						x += (w - tw) * 0.5
						y += (h - th) * 0.5
					else:
						x -= (tw - w) * 0.25
						y -= (th - h) * 0.25
				path = os.path.join(self.app.imagepath, "button-images",
					"%s.svg" % (buttons[i], ))
				img = SVGEditor.get_element(SVGEditor.load_from_file(path), "button")
				img.attrib["transform"] = "translate(%s, %s) scale(%s)" % (
					x - target_x, y - target_y, scale)
				img.attrib["id"] = b
				SVGEditor.add_element(target, img)
			except Exception, err:
				log.warning("Failed to add image for button %s", b)
				log.exception(err)
		e.commit()
