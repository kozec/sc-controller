#!/bin/bash

# Ensure correct cwd
cd "$(dirname "$0")"

# Set PATH
SCRIPTS="$(pwd)/scripts"
export PATH="$SCRIPTS":"$PATH"
export PYTHONPATH=".":"$PYTHONPATH"
export SCC_SHARED="$(pwd)"

if [ x"$1" == x"lldb" ] ; then
	shift
	lldb python2 -- 'scripts/scc-daemon' debug $@
else
	python2 'scripts/scc-daemon' $@
fi
