#!/bin/bash
set -e

export PYTHONPATH="$(pwd)/python"

FILENAME="$1"
if [ -z "$FILENAME" ] ; then
	FILENAME="python/tests"
fi

ninja -C build
py.test "$FILENAME"

