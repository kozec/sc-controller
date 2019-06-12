/*
 * SC Controller - Conversions.
 *
 * Random methods mostly for converting numbers to strings.
 */
#include "scc/utils/strbuilder.h"
#include "scc/conversions.h"
#include <stdio.h>
#include <stdint.h>


static char* AXIS_NAMES[][3] = {
	{ "LStick", "Left", "Right" },				// ABS_X			0x00
	{ "LStick", "Up", "Down" },					// ABS_Y			0x01
	{ "Left Trigger", "Press", "Press" },		// ABS_Z			0x02
	{ "RStick", "Left", "Right" },				// ABS_RX			0x03
	{ "RStick", "Up", "Down" },					// ABS_RY			0x04
	{ "Right Trigger", "Press", "Press" },		// ABS_RZ			0x05
	{ NULL },									// ABS_THROTTLE		0x06
	{ NULL },									// ABS_RUDDER		0x07
	{ "Mouse Wheel", "Up", "Down" },			// REL_WHEEL		0x08
	{ "Horizontal Wheel", "Left", "Right" },	// REL_HWHEEL		0x09
	{ NULL },									// ABS_BRAKE		0x0A
	{ NULL },									//					0x0B
	{ NULL },									//					0x0C
	{ NULL },									//					0x0D
	{ NULL },									//					0x0E
	{ NULL },									//					0x0F
	{ "DPAD", "Left", "Right" },				// ABS_HAT0X		0x10
	{ "DPAD", "Up", "Down" },					// ABS_HAT0Y		0x11
};


char* scc_describe_axis(Axis a, int direction) {
	if ((a >= ABS_X) && (a <= ABS_HAT0Y)) {
		if (AXIS_NAMES[a][0]) {
			if (direction == 0) {
				return strbuilder_fmt("%s", AXIS_NAMES[a][0]);
			} else {
				int lr = (direction < 0) ? 2 : 1;
				return strbuilder_fmt("%s %s",
						AXIS_NAMES[a][0],
						AXIS_NAMES[a][lr]);
			}
		}
	}
	
	return strbuilder_fmt("Axis 0x%x", a);
}

