# PKGBUILD that builds package from git.
# Run 'makepkg -i' and hope for best :)

pkgname=sc-controller-git
pkgver=v0.2.8.1.r3.0c94ff4
pkgrel=1
pkgdesc='User-mode driver and GTK3 based GUI for Steam Controller'
arch=('any')
url='https://github.com/kozec/sc-controller'
license=('GPL2')
depends=('gtk3' 'python2-gobject' 'python2-cairo')
makedepends=('python2-setuptools' 'git')
provides=("${pkgname%-git}")
conflicts=("${pkgname%-git}")
source=('sc-controller'::'git+https://github.com/kozec/sc-controller.git')
md5sums=('SKIP')

pkgver() {
	cd "$srcdir/${pkgname%-git}"
	printf "%s" "$(git describe --tags --long | sed 's/\([^-]*-\)g/r\1/;s/-/./g')"
}

build() {
	cd "$srcdir/${pkgname%-git}"
  	python2 setup.py build
}

package() {
	cd "$srcdir/${pkgname%-git}"
	python2 setup.py install --root="${pkgdir}" --optimize=1
}
