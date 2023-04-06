# SC Controller [![Build Status](https://travis-ci.org/kozec/sc-controller.svg?branch=master)](https://travis-ci.org/kozec/sc-controller)


User-mode driver, mapper and GTK3 based GUI for Steam Controller, DS4 and similar controllers.

[![screenshot1](docs/screenshot1-tn.png?raw=true)](docs/screenshot1.png?raw=true)
[![screenshot2](docs/screenshot2-tn.png?raw=true)](docs/screenshot2.png?raw=true)
[![screenshot3](docs/screenshot3-tn.png?raw=true)](docs/screenshot3.png?raw=true)
[![screenshot3](docs/screenshot4-tn.png?raw=true)](docs/screenshot4.png?raw=true)

## Features
- Allows to setup, configure and use Steam Controller(s) without ever launching Steam
- Supports profiles switchable in GUI or with controller button
- Stick, Pads and Gyroscope input
- Haptic Feedback and in-game Rumble support
- OSD, Menus, On-Screen Keyboard for desktop *and* in games.
- Automatic profile switching based on active window.
- Macros, button cycling, rapid fire, modeshift, mouse regions...
- Emulates Xbox360 controller, mouse, trackball and keyboard.

Based on [Standalone Steam Controller Driver](https://github.com/ynsta/steamcontroller) by [Ynsta](https://github.com/ynsta).

## Like what I'm doing?

[![Help me become filthy rich on Liberapay](https://img.shields.io/badge/Help%20me%20become%20filthy%20rich%20on-Liberapay-yellow.svg)](https://liberapay.com/kozec) <sup>or</sup> [![donate anything with PayPal](https://img.shields.io/badge/donate_anything_with-Paypal-blue.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=77DQD3L9K8RPU&lc=SK&item_name=kozec&item_number=scc&currency_code=EUR&bn=PP%2dDonationsBF%3abtn_donate_LG%2egif%3aNonHosted)

## Packages

 - **Ubuntu (deb-based distros):** Found in [openSUSE Build Service](https://software.opensuse.org/download.html?project=home%3Akozec&package=sc-controller).
 - **Fedora, SUSE (rpm-based distros):** Found in [openSUSE Build Service](https://software.opensuse.org/download.html?project=home%3Akozec&package=sc-controller).
 - **Arch, Manjaro (arch-based distros):** Found in [AUR](https://aur.archlinux.org/packages/sc-controller-git/)
 - **Solus:** Search for `sc-controller` in Software Center or run `sudo eopkg it sc-controller` from a terminal.
 - **Exherbo:** Found in [hardware](https://git.exherbo.org/summer/packages/input/sc-controller)
 - **Void Linux:** Run `xbps-install -S sc-controller` in a terminal.


## Building the package by yourself

### Dependencies
  - python 2.7, GTK 3.22 or newer and [PyGObject](https://live.gnome.org/PyGObject)
  - [python-gi-cairo](https://packages.debian.org/sid/python-gi-cairo) and [gir1.2-rsvg-2.0](https://packages.debian.org/sid/gir1.2-rsvg-2.0) on debian based distros (included in PyGObject elsewhere)
  - [setuptools](https://pypi.python.org/pypi/setuptools)
  - [python-pylibacl](http://pylibacl.k1024.org/) is recommended
  - [python-evdev](https://python-evdev.readthedocs.io/en/latest/) is strongly recommended

### Installing
  - Download and extract  [latest release](https://github.com/kozec/sc-controller/releases/latest)
  - `python3 setup.py build`
  - `python3 setup.py install`


## Running with non distro-specific package          
  - Download and extract [latest release](https://github.com/kozec/sc-controller/releases/latest)
  - Navigate to extracted directory and execute `./run.sh`
