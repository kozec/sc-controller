Notes from building sc-controller (c version) on fresh install of Windows 10

## Build

Install [MSYS2](https://www.msys2.org/) normally, 
- unselect Run MSYS2 after install completes
- use mingw64 shell rather than the default uart64

### x86 [mingw64]
- Install required build packages
    - `pacman -S --needed mingw-w64-i686-pkg-config  mingw-w64-i686-meson mingw-w64-i686-gcc mingw-w64-i686-libmicroutils`

- (optional) install packages needed for gui
    - `pacman -S mingw-w64-i686-glib2 mingw-w64-i686-gtk3 mingw-w64-i686-libusb mingw-w64-i686-python2 mingw-w64-i686-python2-gobject2`
- git clone; cd; git checkout c
- Run meson to generate `build` directory
    - `/mingw64/bin/meson build`
- Run ninja to build everything
    - `/mingw64/bin/ninja -C build`

- Troubleshooting x86: 

- If install fails at any step, install all these dependecies. This personally worked for me to build.
    - `pacman -S --needed mingw-w64-i686-pkg-config mingw-w64-i686-meson mingw-w64-i686-gcc mingw-w64-i686-python2 mingw-w64-i686-gtk3 mingw-w64-i686-libusb mingw-w64-i686-gcc-libs mingw-w64-i686-gettext  mingw-w64-i686-gmp mingw-w64-i686-libiconv  mingw-w64-i686-libsystre mingw-w64-i686-libtre mingw-w64-i686-libwinpthread mingw-w64-i686-mpc mingw-w64-i686-mpfr mingw-w64-i686-gtk3 mingw-w64-i686-python2-gobject2`

### x64 [mingw64]
- Install required build packages
    - `pacman -Sy git mingw-w64-x86_64-meson mingw-w64-x86_64-toolchain`
    - if everything starts to crash with 'fatal error - cygheap base mismatch detected'
      message, close windows terminal and open new instance
- Install dependencies
    - `pacman -S mingw-w64-x86_64-glib2 mingw-w64-x86_64-gtk3`
- (optional) install packages needed for gui
    - `pacman -S mingw-w64-x86_64-python2`
- git clone; cd; git checkout c
- Run meson to generate `build` directory
    - `/mingw64/bin/meson build`
- Run ninja to build everything
    - `/mingw64/bin/ninja -C build`

## Packaging a release
Build using above steps then select a target architecture:
### x64

- Install needed dependencies
    - `pacman -S
    mingw-w64-x86_64-python2-gobject2
    mingw-w64-x86_64-pcre`
- Make the release
    - `./make-win64-release.sh`

