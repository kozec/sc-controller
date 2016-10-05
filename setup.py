#!/usr/bin/env python2
from distutils.core import setup, Extension
from scc.constants import DAEMON_VERSION
import glob

data_files = [
				('share/scc/glade', glob.glob("glade/*.glade")),
				('share/scc/glade/ae', glob.glob("glade/ae/*.glade")),
				('share/scc/images', glob.glob("images/*.svg")),
				('share/scc/images', glob.glob("images/*.svg.json")),
				('share/scc/images/controller-icons', glob.glob("images/controller-icons/*.svg")),
				('share/icons/hicolor/24x24/status', glob.glob("images/24x24/status/*.png")),
				('share/icons/hicolor/22x22/status', glob.glob("images/22x22/status/*.png")),
				('share/scc/default_profiles', glob.glob("default_profiles/*.sccprofile")),
				('share/scc/default_profiles', glob.glob("default_profiles/.*.sccprofile")),
				('share/scc/default_menus', glob.glob("default_menus/*.menu")),
				('share/scc/default_menus', glob.glob("default_menus/.*.menu")),
				('share/pixmaps', [ "images/sc-controller.svg" ]),
				('share/mime/packages', [ "scc-mime-types.xml" ]),
				('share/applications', ['sc-controller.desktop' ]),
				('lib/udev/rules.d', glob.glob('scripts/*.rules')),
				
]

packages = [
	# Required
	'scc', 'scc.drivers', 'scc.lib',
	# Usefull
	'scc.x11', 'scc.osd', 'scc.foreign',
	# GUI
	'scc.gui', 'scc.gui.ae'
]

if __name__ == "__main__":
	setup(name = 'sccontroller',
			version = DAEMON_VERSION,
			description = 'Standalone controller maping tool',
			author = 'kozec',
			packages = packages,
			data_files = data_files,
			scripts = ['scripts/sc-controller', 'scripts/scc-daemon',
				'scripts/scc-osd-message', 'scripts/scc-osd-menu',
				'scripts/scc-osd-keyboard'],
			license = 'GPL2',
			platforms = ['Linux'],
			ext_modules = [
				Extension('libuinput', sources = ['scc/uinput.c']),
			]
	)
