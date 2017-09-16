#!/bin/bash

set -ex		# display commands, terminate after 1st failure
if [ x"$BUILD_APPDIR" == "x" ] ; then
	BUILD_APPDIR=$(pwd)/appimage
fi

# Prepare & build
mkdir -p ${BUILD_APPDIR}/usr
python2 setup.py build
python2 setup.py install --prefix ${BUILD_APPDIR}/usr

# Move udev stuff
mv ${BUILD_APPDIR}/usr/lib/udev/rules.d/90-sc-controller.rules ${BUILD_APPDIR}/
rmdir ${BUILD_APPDIR}/usr/lib/udev/rules.d/
rmdir ${BUILD_APPDIR}/usr/lib/udev/

# Move & patch desktop file
mv ${BUILD_APPDIR}/usr/share/applications/sc-controller.desktop ${BUILD_APPDIR}/
sed -i "s/Icon=.*/Icon=sc-controller/g" ${BUILD_APPDIR}/sc-controller.desktop
sed -i "s/Exec=.*/Exec=.\/usr\/bin\/scc gui/g" ${BUILD_APPDIR}/sc-controller.desktop

# Convert icon
convert -background none ${BUILD_APPDIR}/usr/share/pixmaps/sc-controller.svg ${BUILD_APPDIR}/sc-controller.png

# Copy AppRun script
cp scripts/appimage-AppRun.sh ${BUILD_APPDIR}/AppRun
chmod +x ${BUILD_APPDIR}/AppRun

echo "Run appimagetool ${BUILD_APPDIR} to finish prepared appimage"
