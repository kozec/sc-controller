#!/bin/bash

if [ ! -e libuinput.so ] || [ ! -e libx11osd.so ] ; then
	echo "Required library is missing, building it."
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
	if [ ! -e libx11osd.so ] ; then
		ln -s build/$LIB/libx11osd.so libx11osd.so || exit 1
		echo Symlinked libx11osd.so '->' build/$LIB/libx11osd.so
	fi
	echo ""
fi

python2 scc.py $@
