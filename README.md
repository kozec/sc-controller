SC Controller
=============

User-mode driver and GTK3 based GUI for Steam Controller.

[![screenshot1](docs/screenshot1-tn.png?raw=true)](docs/screenshot1.png?raw=true)
[![screenshot2](docs/screenshot2-tn.png?raw=true)](docs/screenshot2.png?raw=true)

Features:
- Allows to setup, configure and use Steam Controller without ever launching Steam
- Supports profiles switchable in GUI or with controller button
- Emulates XBox360 controller, mouse and keyboard, separately or at once

Based on [Standalone Steam Controller Driver](https://github.com/ynsta/steamcontroller) by [Ynsta](https://github.com/ynsta).

To run:
- download source
- `./run.sh`

To install:
- download source
- `python2 setup.py build`
- `python2 setup.py install`


Dependencies:
- python 2.7, GTK 3.10 or newer and [PyGObject](https://live.gnome.org/PyGObject)
- [python-gi-cairo](https://packages.debian.org/sid/python-gi-cairo) and [gir1.2-rsvg-2.0](https://packages.debian.org/sid/gir1.2-rsvg-2.0) on debian based distros (included in PyGObject elsewhere)
- [setuptools](https://pypi.python.org/pypi/setuptools)
