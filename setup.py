#!/usr/bin/env python2
from distutils.core import setup, Extension
from scc.constants import DAEMON_VERSION
import glob

data_files = [
				('share/scc/glade', glob.glob("glade/*.glade")),
				('share/scc/glade/ae', glob.glob("glade/ae/*.glade")),
				('share/scc/images', glob.glob("images/*.svg")),
				('share/scc/images', glob.glob("images/*.json")),
				('share/scc/images/button-images', glob.glob("images/button-images/*.svg")),
				('share/scc/images/button-images', glob.glob("images/button-images/*.json")),
				('share/scc/images/controller-icons', glob.glob("images/controller-icons/*.svg")),
				('share/scc/images/controller-images', glob.glob("images/controller-images/*.svg")),
				('share/icons/hicolor/24x24/status', glob.glob("images/24x24/status/*.png")),
				('share/icons/hicolor/256x256/status', glob.glob("images/256x256/status/*.png")),
				('share/scc/default_profiles', glob.glob("default_profiles/*.sccprofile")),
				('share/scc/default_profiles', glob.glob("default_profiles/.*.sccprofile")),
				('share/scc/default_menus', glob.glob("default_menus/*.menu")),
				('share/scc/default_menus', glob.glob("default_menus/.*.menu")),
				('share/scc/osd-styles', glob.glob("osd-styles/*.json")),
				('share/scc/osd-styles', glob.glob("osd-styles/*.css")),
				('share/scc/', ["gamecontrollerdb.txt"]),
				('share/pixmaps', [ "images/sc-controller.svg" ]),
				('share/mime/packages', [ "scc-mime-types.xml" ]),
				('share/applications', ['scripts/sc-controller.desktop' ]),
				('lib/udev/rules.d', glob.glob('scripts/*.rules')),
				
] + [ # menu icons subfolders
	(
		'share/scc/images/menu-icons/' + x.split("/")[-1],
		[ x + "/LICENCES" ] + glob.glob(x + "/*.png")
	) for x in glob.glob("images/menu-icons/*")
]


packages = [
	# Required
	'scc', 'scc.drivers', 'scc.lib',
	# Usefull
	'scc.x11', 'scc.osd', 'scc.foreign',
	# GUI
	'scc.gui', 'scc.gui.ae', 'scc.gui.importexport', "scc.gui.creg"
]

if __name__ == "__main__":
	setup(name = 'sccontroller',
			version = DAEMON_VERSION,
			description = 'Standalone controller maping tool',
			author = 'kozec',
			packages = packages,
			data_files = data_files,
			scripts = [
				'scripts/scc-daemon',
				'scripts/sc-controller',
				'scripts/scc',
				'scripts/scc-osd-dialog',
				'scripts/scc-osd-keyboard',
				'scripts/scc-osd-launcher',
				'scripts/scc-osd-menu',
				'scripts/scc-osd-message',
				'scripts/scc-osd-radial-menu',
				'scripts/scc-osd-show-bindings',
			],
			license = 'GPL2',
			platforms = ['Linux'],
			ext_modules = [
				Extension('libuinput', sources = ['scc/uinput.c']),
				Extension('libhiddrv', sources = ['scc/drivers/hiddrv.c']),
				Extension('libsc_by_bt', sources = ['scc/drivers/sc_by_bt.c']),
			]
	)
