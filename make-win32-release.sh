#!/bin/bash
LIBS=(libwinpthread-1.dll libsystre-0.dll libtre-5.dll libusb-1.0.dll libintl-8.dll
		libgcc_s_dw2-1.dll libiconv-2.dll libstdc++-6.dll)
GTK_LIBS=(libgtk-3-0.dll libgdk-3-0.dll libharfbuzz-0.dll libfreetype-6.dll
		libepoxy-0.dll libcairo-gobject-2.dll libpng16-16.dll
		libgraphite2.dll libbz2-1.dll libcairo-2.dll libatk-1.0-0.dll
		libfontconfig-1.dll libgdk_pixbuf-2.0-0.dll libgio-2.0-0.dll
		libglib-2.0-0.dll libgmodule-2.0-0.dll libgobject-2.0-0.dll
		libpango-1.0-0.dll libpangocairo-1.0-0.dll libpangoft2-1.0-0.dll
		libpangowin32-1.0-0.dll libpixman-1-0.dll zlib1.dll libexpat-1.dll
		libffi-6.dll libfribidi-0.dll libpcre-1.dll libthai-0.dll libdatrie-1.dll
		)
DRIVERS=(sc_by_cable sc_dongle)

meson $1
ninja -C $1 || exit 1

mkdir -p release-win32
for d in default_profiles default_menus osd_styles ; do
	cp -vr $d release-win32/
done

cp -v $1/src/daemon/scc-daemon.exe release-win32/
cp -v $1/src/osd/scc-osd-menu.exe release-win32/
# cp -v $1/src/daemon/uinput-win32/libvigemclient.dll release-win32/

for dll in $(find $1 -name "*.dll" -not -name "libscc-drv*") ; do
	cp -v $dll release-win32/ || exit 1
done

mkdir -p release-win32/drivers/
for i in "${DRIVERS[@]}" ; do
	cp -v "$1/src/daemon/drivers/libscc-drv-$i.dll" release-win32/drivers/
done

for i in "${LIBS[@]}" "${GTK_LIBS[@]}" ; do
	[ -e release-win32/$i ] || cp -v $(whereis "$i" | cut -d ":" -f 2) release-win32/
done
