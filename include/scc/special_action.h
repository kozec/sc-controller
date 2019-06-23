/**
 * SC Controller - Special Actions
 *
 * Special Action is "special" since it cannot be handled by input emulation alone.
 * Instead mapper->special_action can implement (or chose to not to) any kind
 * of special actions and handle execution of it in any way that's apropriate.
 *
 * For example, it can spawn new X11 window and display menu in it.
 */
#pragma once
#include "scc/utils/math.h"
#include "scc/controller.h"
#include "scc/parameter.h"
#include <stdbool.h>
#include <unistd.h>

typedef enum SAType {
	SAT_MENU = 1,		// Displays on-screen menu. sa_data is SAMenuActionData*
	SAT_PROFILE = 2,	// Changes profile. sa_data is (char*) representing profile name
	SAT_TURNOFF = 3,	// Turns profile off. sa_data is NULL, ignored.
	SAT_CEMUHOOK = 10,	// Feeds data for CemuHook motion provider. sa_data is (float[6])
} SAType;


typedef struct SAMenuActionData {
	const char*			menu_id;
	HapticData			hdata;
	PadStickTrigger		control_with;
	SCButton			confirm_with;
	SCButton			cancel_with;
	bool				show_with_release;
	double				stick_distance;
	ivec_t				position;
	size_t				size;
} SAMenuActionData;
