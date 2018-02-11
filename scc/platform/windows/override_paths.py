#!/usr/bin/env python2
"""
Override PATH env.variable, import paths and some modules, so SCC can work
with Windows
"""
import sys, os

# TODO: Ensure correct cwd
# cd "$(dirname "$0")"

# Set PATH
SCRIPTS = os.getcwd() + "/scripts"
os.environ["PATH"] = "SCRIPTS;" + os.environ["PATH"]
os.environ["SCC_SHARED"] = os.getcwd()

# Play around with sys.modules
# This simply replaces scc.lib package and some specific modules
# with stuff from scc.platform.windows.
#
# I may invent even more horrible hack later :)
import pkgutil
import scc.platform.windows
import scc.lib

for importer, modname, ispkg in pkgutil.iter_modules(scc.platform.windows.__path__, "scc.platform.windows."):
	module = __import__(modname, fromlist=scc.platform.windows.__path__)
	name = modname.split(".")[-1]
	path = 'scc.lib.%s' % (name,)
	sys.modules[path] = module
	setattr(scc.lib, name, module)

sys.modules['scc.uinput'] = scc.platform.windows.uinput
sys.modules['scc.socket'] = scc.platform.windows.socket
