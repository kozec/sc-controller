SC Controller [![Build Status](https://travis-ci.org/kozec/sc-controller.svg?branch=master)](https://travis-ci.org/kozec/sc-controller)
=============

User-mode driver and GTK3 based GUI for Steam Controller.

[![screenshot1](docs/screenshot1-tn.png?raw=true)](docs/screenshot1.png?raw=true)
[![screenshot2](docs/screenshot2-tn.png?raw=true)](docs/screenshot2.png?raw=true)

##### Features
- Allows to setup, configure and use Steam Controller(s) without ever launching Steam
- Supports profiles switchable in GUI or with controller button
- Stick, Pads and Gyroscope input
- Haptic Feedback and in-game Rumble support
- OSD, Menus, On-Screen Keyboard for desktop *and* in games.
- Automatic profile switching based on active window.
- Macros, button cycling, rapid fire, modeshift, mouse regions...
- Emulates XBox360 controller, mouse, trackball and keyboard.

Based on [Standalone Steam Controller Driver](https://github.com/ynsta/steamcontroller) by [Ynsta](https://github.com/ynsta).

##### Like what I'm doing?

[![Help me become filthy rich on Patreon](https://img.shields.io/badge/Help_me_become_filthy_rich_on-Patreon-Orange.svg)](https://www.patreon.com/kozec) <sup>or</sup> [![pay what you want with PayPal](https://img.shields.io/badge/pay_what_you_want_with-Paypal-yellow.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=77DQD3L9K8RPU&lc=SK&item_name=kozec&item_number=scc&currency_code=EUR&bn=PP%2dDonationsBF%3abtn_donate_LG%2egif%3aNonHosted)
##### Packages
- Ubuntu (deb-based distros): in [OpenSUSE Build Service](http://software.opensuse.org/download.html?project=home%3Akozec&package=sc-controller).
- Fedora, SUSE (rpm-based distros): in [OpenSUSE Build Service](http://software.opensuse.org/download.html?project=home%3Akozec&package=sc-controller).
- Solus: search for `sc-controller` in Software Center
- Exherbo: in [hardware](https://git.exherbo.org/summer/packages/input/sc-controller)
- Voidlinux: [template available](https://github.com/Vintodrimmer/void-packages/blob/sc-controller-branch/srcpkgs/sc-controller/template)

##### To run without package
- download and extract [latest release](https://github.com/kozec/sc-controller/releases/latest)
- navigate to extracted directory and execute `./run.sh`

##### To install without package
- download and extract  [latest release](https://github.com/kozec/sc-controller/releases/latest)
- `python2 setup.py build`
- `python2 setup.py install`


##### Dependencies
- python 2.7, GTK 3.10 or newer and [PyGObject](https://live.gnome.org/PyGObject)
- [python-gi-cairo](https://packages.debian.org/sid/python-gi-cairo) and [gir1.2-rsvg-2.0](https://packages.debian.org/sid/gir1.2-rsvg-2.0) on debian based distros (included in PyGObject elsewhere)
- [python-pylibacl](http://pylibacl.k1024.org/)
- [setuptools](https://pypi.python.org/pypi/setuptools)
