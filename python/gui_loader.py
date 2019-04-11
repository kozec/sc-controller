import sys
import gi
gi.require_version('Gtk', '3.0') 
gi.require_version('Rsvg', '2.0') 
try:
	gi.require_version('GdkX11', '3.0') 
except ValueError: pass

from scc.tools import init_logging
from scc.paths import get_share_path
init_logging()

import os, sys
sys.argv = [ "sc-controller" ]

from gi.repository import Gtk, GObject
glades = os.path.join(get_share_path(), "glade")
images = os.path.join(get_share_path(), "images")
if Gtk.IconTheme.get_default():
	Gtk.IconTheme.get_default().append_search_path(images)
GObject.threads_init()

from scc.gui.app import App
App(glades, images).run(sys.argv)

