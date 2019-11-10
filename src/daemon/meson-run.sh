#!/bin/bash
cd "$MESON_BUILD_ROOT"
PATHS="%PATH%"
# PATHS="%CD%\\src\\osd;$PATHS"
PATHS="%CD%\\src\\client;$PATHS"
PATHS="%CD%\\src\\osd\\common;$PATHS"
PATHS="%CD%\\src\\virtual-device;$PATHS"
cmd.exe /C "set PATH=$PATHS & src\\daemon\\scc-daemon.exe"
exit $?

