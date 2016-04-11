#!/usr/bin/env python
from distutils.core import setup, Extension

uinput = Extension('libuinput',
                   sources = ['scc/uinput.c'])

setup(name='sccontroller',
      version='1.0',
      description='Standalone controller maping tool',
      author='kozec',
      package_dir={'scc': 'scc'},
      packages=['scc'],
      scripts=['scc.py'],
      license='GPL2',
      platforms=['Linux'],
      ext_modules=[uinput, ])
