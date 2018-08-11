#!/bin/bash
export PATH=${APPDIR}:${APPDIR}/usr/bin:$PATH
export LD_LIBRARY_PATH=${APPDIR}/usr/lib:$LD_LIBRARY_PATH
export LD_LIBRARY_PATH=${APPDIR}/usr/lib64:$LD_LIBRARY_PATH
export GI_TYPELIB_PATH=${APPDIR}/usr/lib/girepository-1.0:/usr/lib/girepository-1.0
export GDK_PIXBUF_MODULEDIR=${APPDIR}/usr/lib/gdk-pixbuf-2.0/2.10.0/loaders
export PYTHONPATH=${APPDIR}/usr/lib/python2.7/site-packages:$PYTHONPATH
export PYTHONPATH=${APPDIR}/usr/lib64/python2.7/site-packages:$PYTHONPATH
export SCC_SHARED=${APPDIR}/usr/share/scc

function dependency_check_failed() {
	# This checks 4 different ways to open error message in addition to
	# throwing it to screen directly
	>&2 cat /tmp/scc.depcheck.$$.txt
	
	[ -e /usr/bin/zenity ] && run_and_die /usr/bin/zenity --error --no-wrap --text "$(cat /tmp/scc.depcheck.$$.txt)"
	[ -e /usr/bin/yad ] && run_and_die /usr/bin/yad --error --text "$(cat /tmp/scc.depcheck.$$.txt)"
	[ -e /usr/bin/Xdialog ] && run_and_die /usr/bin/Xdialog --textbox "/tmp/scc.depcheck.$$.txt" 10 100
	[ -e /usr/bin/xdg ] && run_and_die /usr/bin/xdg-open "/tmp/scc.depcheck.$$.txt"
	exit 1
}

function run_and_die() {
	"$@"
	exit 1
}

# Check dependencies 1st
python2 ${APPDIR}/usr/bin/scc dependency-check &>/tmp/scc.depcheck.$$.txt \
	|| dependency_check_failed
rm /tmp/scc.depcheck.$$.txt || true

# Pre-parse arguments
ARG1=$1
if [ "x$ARG1" == "x" ] ; then
	# Start gui if no arguments are passed
	ARG1="gui"
else
	shift
fi

# Start
export GDK_PIXBUF_MODULE_FILE=${APPDIR}/../$$-gdk-pixbuf-loaders.cache
gdk-pixbuf-query-loaders >"$GDK_PIXBUF_MODULE_FILE"
python2 ${APPDIR}/usr/bin/scc $ARG1 $@
rm "$GDK_PIXBUF_MODULE_FILE" &>/dev/null

