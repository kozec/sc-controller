SC Controller
=============

User-mode driver and GTK3 based GUI for Steam Controller.

[![screenshot1](docs/screenshot1-tn.png?raw=true)](docs/screenshot1.png?raw=true)
[![screenshot2](docs/screenshot2-tn.png?raw=true)](docs/screenshot2.png?raw=true)

##### Features
- Allows to setup, configure and use Steam Controller without ever launching Steam
- Supports profiles switchable in GUI or with controller button
- Stick, Pads and Gyroscope input
- Haptic Feedback support
- OSD, Menus, On-Screen Keyboard for desktop *and* in games.
- Macros, rapid fire, modeshift, mouse regions...
- Emulates XBox360 controller, mouse, trackball and keyboard.

Based on [Standalone Steam Controller Driver](https://github.com/ynsta/steamcontroller) by [Ynsta](https://github.com/ynsta).

##### Like what I'm doing?
<a href="https://www.patreon.com/kozec">Help me become filthy rich on <img src="http://kozec.com/patreon-logo.png"></a>

##### Packages
- Ubuntu (deb-based distros): in [OpenSUSE Build Service](http://software.opensuse.org/download.html?project=home%3Akozec&package=sc-controller).
- Fedora, SUSE (rpm-based distros): in [OpenSUSE Build Service](http://software.opensuse.org/download.html?project=home%3Akozec&package=sc-controller).
- Arch, Manjaro: in [AUR](https://aur.archlinux.org/packages/sc-controller-git/)

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
- [setuptools](https://pypi.python.org/pypi/setuptools)
