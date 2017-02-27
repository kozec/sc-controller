#!/usr/bin/env python2
from __future__ import unicode_literals
from scc.tools import _

from gi.repository import Gtk, Gio
from scc.tools import get_profiles_path, find_profile, find_menu
from scc.parser import ActionParser, TalkingActionParser
from scc.profile import Profile

import sys, os, json, tarfile, tempfile, logging
log = logging.getLogger("IE.ImportSSCC")

class ImportSccprofile(object):
	def __init__(self):
		pass
	
	
	def on_btImportSccprofile_clicked(self, *a):
		# Create filters
		f1 = Gtk.FileFilter()
		f1.set_name("SC-Controller Profile or Archive")
		f1.add_pattern("*.sccprofile")
		f1.add_pattern("*.sccprofile.tar.gz")
		
		# Create dialog
		d = Gtk.FileChooserNative.new(_("Import Profile..."),
				self.window, Gtk.FileChooserAction.OPEN)
		d.add_filter(f1)
		if d.run() == Gtk.ResponseType.ACCEPT:
			pass

