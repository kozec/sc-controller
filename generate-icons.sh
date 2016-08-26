#!/bin/bash
# Used to generate some icons
# Requires inkscape and imagemagick pacages

ICODIR=./images/		# Directory with icons

for size in 24 ; do
	for state in alive dead error unknown ; do
		echo scc-${state}.png
		inkscape ${ICODIR}/scc-${state}.svg \
			--export-area-page \
			--export-png=${ICODIR}/${size}x${size}/status/scc-${state}.png \
			--export-width=${size} --export-height=${size}
	done
done
