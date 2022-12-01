Notes from building sc-controller (c version) on fresh install of Windows 10

- Install [MSYS2](https://www.msys2.org/) normally
- Install required build packages
    - `pacman -Sy git mingw-w64-x86_64-meson mingw-w64-x86_64-toolchain`
    - if everything starts to crash with 'fatal error - cygheap base mismatch detected'
      message, close windows terminal and open new instance
- Install dependencies
    - `pacman -S mingw-w64-x86_64-glib2 mingw-w64-x86_64-gtk3`
- (optional) install packages needed for gui
    - `pacman -S mingw-w64-x86_64-python2 mingw-w64-x86_64-python2-cairo mingw-w64-x86_64-python2-gobject`
- git clone; cd; git checkout c
- Run meson to generate `build` directory
    - `/mingw64/bin/meson build`
- Run ninja to build everything
    - `/mingw64/bin/ninja -C build`

