# PKGBUILD that builds package directly from source tree.
# Run 'makepkg -i' and hope for best :)

pkgname=sc-controller
pkgver=0.1
pkgrel=1
pkgdesc='User-mode driver and GTK3 based GUI for Steam Controller'
arch=('any')
url='https://github.com/kozec/sc-controller'
license=('GPL2')
depends=('gtk3' 'python2-gobject' 'python2-cairo')
makedepends=('python2-setuptools')
source=()

build() {
  cd ${startdir}
  python2 setup.py build
}

package() {
  cd ${startdir}
  python2 setup.py install --root="${pkgdir}" --optimize=1
}