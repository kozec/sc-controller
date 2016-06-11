#!/bin/bash

# Ensure correct cwd
cd "$(dirname "$0")"

# Check if libuinput.so is available
if [ ! -e libuinput.so ] ; then
	echo "libuinput.so is missing, building one"
	echo "Please wait, this should be done only once."
	echo ""
	
	python2 setup.py build || exit 1
	echo ""
	
	# Next line generates string like 'lib.linux-x86_64-2.7', directory where libuinput.so was just generated
	LIB=$( python2 -c 'import platform ; print "lib.linux-%s-%s.%s" % ((platform.machine(),) + platform.python_version_tuple()[0:2])' )
	
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
