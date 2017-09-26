#!/bin/bash

# Ensure correct cwd
cd "$(dirname "$0")"

# Check for libuinput.so version
UNPUT_MODULE_VERSION=7
REPORTED_VERSION=$(PYTHONPATH="." python2 -c 'import os, ctypes; lib=ctypes.CDLL("./libuinput.so"); print lib.uinput_module_version()')
if [ x"$UNPUT_MODULE_VERSION" != x"$REPORTED_VERSION" ] ; then
	echo "libuinput.so is outdated or missing, building one"
	echo "Please wait, this should be done only once."
	echo ""
	
	# Next line generates string like 'lib.linux-x86_64-2.7', directory where libuinput.so was just generated
	LIB=$( python2 -c 'import platform ; print "lib.linux-%s-%s.%s" % ((platform.machine(),) + platform.python_version_tuple()[0:2])' )
	
	if [ -e build/$LIB/libuinput.so ] ; then
		rm build/$LIB/libuinput.so || exit 1
	fi
	
	python2 setup.py build || exit 1
	echo ""
	
	if [ ! -e libuinput.so ] ; then
		ln -s build/$LIB/libuinput.so libuinput.so || exit 1
		echo Symlinked libuinput.so '->' build/$LIB/libuinput.so
	fi
	echo ""
fi

# Set PATH
SCRIPTS="$(pwd)/scripts"
export PATH="$SCRIPTS":"$PATH"
export PYTHONPATH=".":"$PYTHONPATH"
export SCC_SHARED="$(pwd)"

# Execute
python2 'scripts/sc-controller' $@
