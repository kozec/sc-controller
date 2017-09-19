#!/bin/bash
EVDEV_VERSION=0.7.0
if [ x"$BUILD_APPDIR" == "x" ] ; then
	BUILD_APPDIR=$(pwd)/appimage
fi

set -ex		# display commands, terminate after 1st failure

# Download deps
wget -c "https://github.com/gvalkov/python-evdev/archive/v${EVDEV_VERSION}.tar.gz" -O /tmp/python-evdev-${EVDEV_VERSION}.tar.gz

# Prepare & build
mkdir -p ${BUILD_APPDIR}/usr
python2 setup.py build
python2 setup.py install --prefix ${BUILD_APPDIR}/usr

# Unpack & build deps
pushd /tmp
tar xzf python-evdev-${EVDEV_VERSION}.tar.gz
cd python-evdev-${EVDEV_VERSION}
python2 setup.py build
PYTHONPATH=${BUILD_APPDIR}/usr/lib/python2.7/site-packages python2 setup.py install --prefix ${BUILD_APPDIR}/usr
popd

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

# Copy appdata.xml
mkdir -p ${BUILD_APPDIR}/usr/share/metainfo/
cp scripts/sc-controller.appdata.xml ${BUILD_APPDIR}/usr/share/metainfo/sc-controller.appdata.xml

# Copy AppRun script
cp scripts/appimage-AppRun.sh ${BUILD_APPDIR}/AppRun
chmod +x ${BUILD_APPDIR}/AppRun

echo "Run appimagetool ${BUILD_APPDIR} to finish prepared appimage"
