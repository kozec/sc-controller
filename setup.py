#!/usr/bin/env python
from distutils.core import setup, Extension
import glob

data_files = [
				('share/scc/glade', glob.glob("glade/*.glade")),
				('share/scc/glade/ae', glob.glob("glade/ae/*.glade")),
				('share/scc/images', glob.glob("images/*.svg")),
				('share/scc/default_profiles', glob.glob("default_profiles/*.sccprofile")),
				('share/pixmaps', [ "images/sc-controller.svg" ]),
				('share/applications', ['sc-controller.desktop'] )
				
]

setup(name='sccontroller',
		version='1.0',
		description='Standalone controller maping tool',
		author='kozec',
		packages=['scc', 'scc.gui', 'scc.gui.ae', 'scc.lib'],
		data_files = data_files,
		scripts=['scripts/sc-controller', 'scripts/scc-daemon'],
		license='GPL2',
		platforms=['Linux'],
		ext_modules=[
			Extension('libuinput', sources = ['scc/uinput.c']),
		]
)
