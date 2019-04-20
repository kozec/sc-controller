#!/bin/bash
LIBS=(libwinpthread-1.dll libsystre-0.dll libtre-5.dll libusb-1.0.dll
		libintl-8.dll libgcc_s_dw2-1.dll libiconv-2.dll libstdc++-6.dll
		libpython2.7.dll libgirepository-1.0-1.dll)
GTK_LIBS=(libgtk-3-0.dll libgdk-3-0.dll libharfbuzz-0.dll libfreetype-6.dll
		libepoxy-0.dll libcairo-gobject-2.dll libpng16-16.dll
		libgraphite2.dll libbz2-1.dll libcairo-2.dll libatk-1.0-0.dll
		libfontconfig-1.dll libgdk_pixbuf-2.0-0.dll libgio-2.0-0.dll
		libglib-2.0-0.dll libgmodule-2.0-0.dll libgobject-2.0-0.dll
		libpango-1.0-0.dll libpangocairo-1.0-0.dll libpangoft2-1.0-0.dll
		libpangowin32-1.0-0.dll libpixman-1-0.dll zlib1.dll libexpat-1.dll
		libffi-6.dll libfribidi-0.dll libpcre-1.dll libthai-0.dll liblzma-5.dll
		librsvg-2-2.dll libcroco-0.6-3.dll libxml2-2.dll libdatrie-1.dll
		libcrypto-1_1.dll)
GTK_ICONS=(
		status/image-missing.png
		status/dialog-information.png
		status/dialog-warning.png
		status/dialog-error.png
		status/checkbox-symbolic.symbolic.png
		status/checkbox-mixed-symbolic.symbolic.png
		status/checkbox-checked-symbolic.symbolic.png
		actions/open-menu-symbolic.symbolic.png
		actions/window-close-symbolic.symbolic.png
		actions/window-maximize-symbolic.symbolic.png
		actions/window-restore-symbolic.symbolic.png
		actions/window-minimize-symbolic.symbolic.png
		actions/list-add-symbolic.symbolic.png
		actions/list-remove-symbolic.symbolic.png
		actions/pan-up-symbolic.symbolic.png
		actions/pan-start-symbolic.symbolic.png
		actions/pan-end-symbolic.symbolic.png
		actions/pan-down-symbolic.symbolic.png
)
DRIVERS=(sc_by_cable sc_dongle)

export PROCESSOR_ARCHITEW6432=x86
# meson $1
ninja -C $1 || exit 1

mkdir -p release-win32/python
mkdir -p release-win32/share
mkdir -p release-win32/lib
cp -vur share/* release-win32/share
cp -vur python/scc release-win32/python
cp -vur /mingw32/lib/python2.7 release-win32/lib
cp -vu python/gui_loader.py release-win32/python/
cp -vur /mingw32/lib/girepository-1.0/ release-win32/lib
cp -vur /mingw32/lib/gdk-pixbuf-2.0/ release-win32/lib
cp -vu	/mingw32/bin/gspawn-win32-helper.exe \
		/mingw32/bin/gspawn-win32-helper-console.exe release-win32/

find release-win32/python/ -iname "*.pyc" -delete

for exe in $(find $1 -name "scc-*.exe" -or -name "sc-*.exe") ; do
	cp -vu $exe release-win32/ || exit 1
done

for dll in $(find $1 -name "*.dll" -and -not -name "libscc-drv*" -and -not -name "libscc-menugen-*" ) ; do
	cp -vu $dll release-win32/ || exit 1
done

mkdir -p release-win32/drivers/
for i in "${DRIVERS[@]}" ; do
	cp -vu "$1/src/daemon/drivers/libscc-drv-$i.dll" release-win32/drivers/
done

mkdir -p release-win32/menu-generators/
cp -vu "$1"/src/menu-generators/*.dll release-win32/menu-generators

for i in "${LIBS[@]}" "${GTK_LIBS[@]}" ; do
	[ -e release-win32/$i ] || cp -v $(whereis "$i" | cut -d ":" -f 2) release-win32/
done

mkdir -p release-win32/share/images/status
mkdir -p release-win32/share/images/actions
for i in "${GTK_ICONS[@]}" ; do
	n=$(basename "$i")
	[ -e release-win32/share/images/"$n" ] || cp -v \
		/mingw32/share/icons/Adwaita/16x16/"$i" release-win32/share/images/"$n"
done

