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

import os, sys, json, logging
log = logging.getLogger("ContImage")


class ControllerImage(SVGWidget):
	DEFAULT  = "sc"
	BUTTONS_WITH_IMAGES = (
		SCButtons.A, SCButtons.B, SCButtons.X, SCButtons.Y,
		SCButtons.BACK, SCButtons.C, SCButtons.START
	)
	
	def __init__(self, app, config=None):
		self.app = app
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
		data['gui'] = data.get('gui', {})
		data['gui']['background'] = data['gui'].get("background", "sc")
		data['gui']['buttons'] = data['gui'].get("buttons") or self._get_default_images()
		return data
	
	
	def load_config(self, filename):
		"""
		Loads controller settings from config file sent by daemon.
		May be None or invalid, in which case, defaults are loaded.
		"""
		if filename:
			if "/" not in filename:
				filename = os.path.join(self.app.imagepath, filename)
			try:
				data = json.loads(open(filename, "r").read()) or {}
			except Exception, e:
				log.exception(e)
				data = {}
		else:
			data = {}
		return self._ensure_config(data)
	
	
	def use_config(self, config):
		self.current = self._ensure_config(config)
		self.set_image(os.path.join(self.app.imagepath,
			"controller-images/%s.svg" % (config["gui"]["background"], )))
		self._fill_button_images(config["gui"]["buttons"])
		self.hilight({})
	
	
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
		file("/tmp/a.svg", "w").write(e.to_string())
		e.commit()
