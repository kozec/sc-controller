#!/bin/bash
APP="sc-controller"
EXEC="scc"

EVDEV_VERSION=0.7.0
[ x"$BUILD_APPDIR" == "x" ] && BUILD_APPDIR=$(pwd)/appimage


function download_dep() {
	NAME=$1
	URL=$2
	if [ -e ../../${NAME}.obstargz ] ; then
		# Special case for OBS
		cp ../../${NAME}.obstargz /tmp/${NAME}.tar.gz
	elif [ -e ${NAME}.tar.gz ] ; then
		cp ${NAME}.tar.gz /tmp/${NAME}.tar.gz
	else
		wget -c "${URL}" -O /tmp/${NAME}.tar.gz
	fi
}

function build_dep() {
	NAME="$1"
	mkdir -p /tmp/${NAME}
	pushd /tmp/${NAME}
	tar --extract --strip-components=1 -f /tmp/${NAME}.tar.gz
	python2 setup.py build
	python2 setup.py install --prefix ${BUILD_APPDIR}/usr
	popd
}

set -ex		# display commands, terminate after 1st failure

# Download deps
download_dep "python-evdev-0.7.0" "https://github.com/gvalkov/python-evdev/archive/v0.7.0.tar.gz"
download_dep "pylibacl-0.5.3" "https://github.com/iustin/pylibacl/releases/download/pylibacl-v0.5.3/pylibacl-0.5.3.tar.gz"

# Prepare & build
export PYTHONPATH=${BUILD_APPDIR}/usr/lib/python2.7/site-packages/
mkdir -p "$PYTHONPATH"/site-packages/
if [[ $(grep ID_LIKE /etc/os-release) == *"suse"* ]] ; then
	# Special handling for OBS
	ln -s lib64 ${BUILD_APPDIR}/usr/lib
	export PYTHONPATH="$PYTHONPATH":${BUILD_APPDIR}/usr/lib64/python2.7/site-packages/
fi

build_dep "python-evdev-0.7.0"
build_dep "pylibacl-0.5.3"
python2 setup.py build
python2 setup.py install --prefix ${BUILD_APPDIR}/usr

# Move udev stuff
mv ${BUILD_APPDIR}/usr/lib/udev/rules.d/90-${APP}.rules ${BUILD_APPDIR}/
rmdir ${BUILD_APPDIR}/usr/lib/udev/rules.d/
rmdir ${BUILD_APPDIR}/usr/lib/udev/

# Move & patch desktop file
mv ${BUILD_APPDIR}/usr/share/applications/${APP}.desktop ${BUILD_APPDIR}/
sed -i "s/Icon=.*/Icon=${APP}/g" ${BUILD_APPDIR}/${APP}.desktop
sed -i "s/Exec=.*/Exec=.\/usr\/bin\/scc gui/g" ${BUILD_APPDIR}/${APP}.desktop

# Convert icon
convert -background none ${BUILD_APPDIR}/usr/share/pixmaps/${APP}.svg ${BUILD_APPDIR}/${APP}.png

# Copy appdata.xml
mkdir -p ${BUILD_APPDIR}/usr/share/metainfo/
cp scripts/${APP}.appdata.xml ${BUILD_APPDIR}/usr/share/metainfo/${APP}.appdata.xml

# Copy AppRun script
cp scripts/appimage-AppRun.sh ${BUILD_APPDIR}/AppRun
chmod +x ${BUILD_APPDIR}/AppRun

echo "Run appimagetool -n ${BUILD_APPDIR} to finish prepared appimage"
