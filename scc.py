#!/usr/bin/env python2
import os, sys, signal

def sigint(*a):
	print("\n*break*")
	sys.exit(0)

if __name__ == "__main__":
	signal.signal(signal.SIGINT, sigint)

	import gi
	gi.require_version('Gtk', '3.0') 
	gi.require_version('Rsvg', '2.0') 
	
	from scc.tools import init_logging
	init_logging()

	from gi.repository import Gtk
	Gtk.IconTheme.get_default().append_search_path(os.path.join(os.getcwd(), "images"))
	
	from scc.gui.app import App
	App(".", "./images").run(sys.argv)
