#!/usr/bin/env python
from distutils.core import setup, Extension
import glob

data_files = [
				('share/scc/glade', glob.glob("glade/*.glade")),
				('share/scc/glade/ae', glob.glob("glade/ae/*.glade")),
				('share/scc/images', glob.glob("images/*.svg")),
				('share/scc/default_profiles', glob.glob("default_profiles/*.sccprofile")),
				('share/scc/default_menus', glob.glob("default_menus/*.menu")),
				('share/pixmaps', [ "images/sc-controller.svg" ]),
				('share/applications', ['sc-controller.desktop'] )
				
]

setup(name='sccontroller',
		version='0.2.6',
		description='Standalone controller maping tool',
		author='kozec',
		packages=['scc', 'scc.gui', 'scc.gui.ae', 'scc.lib', 'scc.osd'],
		data_files = data_files,
		scripts=['scripts/sc-controller', 'scripts/scc-daemon',
			'scripts/scc-osd-message', 'scripts/scc-osd-menu',
			'scripts/scc-osd-keyboard'],
		license='GPL2',
		platforms=['Linux'],
		ext_modules=[
			Extension('libuinput', sources = ['scc/uinput.c']),
		]
)
