#!/bin/bash

# Ensure correct cwd
cd "$(dirname "$0")"

# Set PATH
SCRIPTS="$(pwd)/scripts"
export PATH="$SCRIPTS":"$PATH"
export PYTHONPATH=".":"$PYTHONPATH"
export SCC_SHARED="$(pwd)"

python2 'scripts/scc-daemon' $@
# gdb --args python2 'scripts/scc-daemon' $@
