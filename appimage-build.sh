#!/bin/bash

set -e	# terminate after 1st failure
DIR=$(pwd)/appimage

# Prepare & build
mkdir -p ${DIR}/usr
python2 setup.py build
python2 setup.py install --prefix ${DIR}/usr

# Move udev stuff
mv ${DIR}/usr/lib/udev/rules.d/90-sc-controller.rules ${DIR}/
rmdir ${DIR}/usr/lib/udev/rules.d/
rmdir ${DIR}/usr/lib/udev/

# Move & patch desktop file
mv ${DIR}/usr/share/applications/sc-controller.desktop ${DIR}/
sed -i "s/Icon=.*/Icon=sc-controller/g" ${DIR}/sc-controller.desktop
sed -i "s/Exec=.*/Exec=.\/usr\/bin\/scc gui/g" ${DIR}/sc-controller.desktop

# Convert icon
convert -background none ${DIR}/usr/share/pixmaps/sc-controller.svg ${DIR}/sc-controller.png

# Copy AppRun script
cp scripts/appimage-AppRun.sh ${DIR}/AppRun
chmod +x ${DIR}/AppRun

# Generate appimage
appimagetool ${DIR}