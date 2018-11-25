SC Controller
=============

User-mode driver and mapper for Steam Controller, DS4 and similar controllers.

[![screenshot1](docs/screenshot1-tn.png?raw=true)](docs/screenshot1.png?raw=true)
[![screenshot2](docs/screenshot2-tn.png?raw=true)](docs/screenshot2.png?raw=true)
[![screenshot3](docs/screenshot3-tn.png?raw=true)](docs/screenshot3.png?raw=true)
[![screenshot3](docs/screenshot4-tn.png?raw=true)](docs/screenshot4.png?raw=true)

-----------

## WIP win32/linux/android port in c

Hi there. What you are browsing is WIP branch in which I'm rewriting major parts of SCC into much more portable and much less python requiring code.

It should be somehow usable, but only very basic stuff works right now.
See this [wiki page](https://github.com/kozec/sc-controller/wiki/Running-SC-Controller-on-Windows) for how to run it.

-----------

#### Building

Navigate to directory with sources and use meson to compile:

```
# on Linux
$ meson build
$ ninja -C build
$ SCC_SHARED=$(pwd) build/src/daemon/scc-daemon
```

```
# on Windows (with mingw)
$ PROCESSOR_ARCHITEW6432=x86 meson build
$ ninja -C build
$ build/src/daemon/scc-daemon
```
