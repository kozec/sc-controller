#!/bin/bash
cd "$MESON_BUILD_ROOT"
ninja || exit 1

if [[ $(uname) == *"MINGW"??"_NT"* ]] ; then
	export SCC_SHARED="$MESON_BUILD_ROOT\\..\\"
	PATHS="%PATH%"
	PATHS="%CD%\\src\\client;$PATHS"
	PATHS="%CD%\\src\\osd\\common;$PATHS"
	PATHS="%CD%\\src\\osd\\menus;$PATHS"
	PATHS="%CD%\\src\\virtual-device;$PATHS"
	EXE="$(echo "$1" | tr \"/\" \"\\\\\").exe"
	export IM="$(echo "$1" | rev | cut -d / -f 1 | rev)"
	shift
	PARS="$(echo $@ | tr \"/\" \"\\\\\")"
	
	function kill_it() {
		taskkill -F -IM "$IM".exe
	};
	
	trap kill_it SIGINT
	
	echo "Working directory: $(pwd)"
	cmd.exe /C "set PATH=$PATHS & $EXE $PARS"
	exit $?
else
	export SCC_SHARED="$MESON_BUILD_ROOT/../"
	export PYTHON_PATH="$MESON_BUILD_ROOT/../python"
	$@
	exit $?
fi

