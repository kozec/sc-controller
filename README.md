SC Controller
=============

User-mode driver and mapper for Steam Controller, DS4 and similar controllers.

[![screenshot1](docs/screenshot1-tn.png?raw=true)](docs/screenshot1.png?raw=true)
[![screenshot2](docs/screenshot2-tn.png?raw=true)](docs/screenshot2.png?raw=true)
[![screenshot3](docs/screenshot3-tn.png?raw=true)](docs/screenshot3.png?raw=true)
[![screenshot3](docs/screenshot4-tn.png?raw=true)](docs/screenshot4.png?raw=true)

-----------

## WIP Windows/BSD/Linux/android port in c

Hi there. What you are browsing is WIP branch in which I'm rewriting major parts of SCC into much more portable and much less python requiring code.

It should be somehow usable, but there is no GUI and only very basic OSD menu right now.
See this [wiki page](https://github.com/kozec/sc-controller/wiki/Running-SC-Controller-on-Windows) for how to run it.

-----------

#### Like what I'm doing?

[![Help me become filthy rich on Liberapay](https://img.shields.io/badge/Help%20me%20become%20filthy%20rich%20on-Liberapay-yellow.svg)](https://liberapay.com/kozec) <sup>or</sup> [![donate anything with PayPal](https://img.shields.io/badge/donate_anything_with-Paypal-blue.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=77DQD3L9K8RPU&lc=SK&item_name=kozec&item_number=scc&currency_code=EUR&bn=PP%2dDonationsBF%3abtn_donate_LG%2egif%3aNonHosted)


#### Building

Navigate to directory with sources and use meson to compile:

###### on Linux
```
$ meson build
$ ninja -C build
$ ninja -C build scc-daemon
```

###### on Windows
```
# (you'll need mingw)
$ pacman -S --needed mingw-w64-i686-pkg-config mingw-w64-i686-meson mingw-w64-i686-gcc mingw-w64-i686-python2 mingw-w64-i686-gtk3 mingw-w64-i686-libusb mingw-w64-i686-libmicroutils
$ export PROCESSOR_ARCHITEW6432=x86
$ meson build
$ ninja -C build sc-controller  # start GUI
$ ninja -C build scc-daemon     # start without gui to check why it doesn't work
```

###### on OpenBSD or NetBSD
```
# (install pkg-config, ninja-build and meson packages first. Meson is available as pip package)
$ meson build
$ ninja -C build
$ ninja -C build scc-daemon
```

