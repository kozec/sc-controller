/**
 * SC Controller - StickController
 *
 * Utility class that gets fed by with stick positions and repeatedly calls
 * callbacks with computed direction that stick is facing.
 * This is used used as input for menu navigation.
 */

#define LOG_TAG "OSD"
#include "scc/utils/logging.h"
#include "scc/controller.h"
#include "../osd.h"
#include <stdbool.h>
#include <stdint.h>

typedef enum {
	DIR_NONE = 0,
	DIR_UP = 1,
	DIR_DOWN = 2,
	DIR_LEFT = 3,
	DIR_RIGHT = 4,
} Direction;

struct StickController {
	Direction					direction;
	void*						userdata;
	guint						timer;
	StickControllerCallback		cb;
};

static int DIRECTION_TO_XY[5][2] = {
	/* DIR_NONE = 0 */		{ 0, 0 },
	/* DIR_UP = 1 */		{ 0, -1 },
	/* DIR_DOWN = 2 */		{ 0, 1 },
	/* DIR_LEFT = 3 */		{ -1, 0 },
	/* DIR_RIGHT = 4 */		{ 1, 0 },
};


StickController* stick_controller_create(StickControllerCallback cb, void* userdata) {
	StickController* sc = malloc(sizeof(StickController));
	if (sc == NULL) return NULL;
	sc->direction = 0;
	sc->userdata = userdata;
	sc->timer = 0;
	sc->cb = cb;
	return sc;
}

static gboolean stick_controller_timeout_cb(gpointer _sc);

static void stick_controller_move(StickController* sc) {
	sc->cb(DIRECTION_TO_XY[sc->direction][0], DIRECTION_TO_XY[sc->direction][1], sc->userdata);
	if (sc->direction == DIR_NONE) {
		if (sc->timer != 0) {
			g_source_remove(sc->timer);
			sc->timer = 0;
		}
	} else {
		sc->timer = g_timeout_add(STICK_CONTROLLER_REPEAT_DELAY, &stick_controller_timeout_cb, sc);
	}
}

static gboolean stick_controller_timeout_cb(gpointer _sc) {
	StickController* sc = (StickController*)_sc;
	sc->timer = 0;
	stick_controller_move(sc);
	return false;
}

void stick_controller_feed(StickController* sc, int values[]) {
	Direction direction = DIR_NONE;
	// Y
	if (values[1] < STICK_PAD_MIN / 2)
		direction = DIR_DOWN;
	else if (values[1] > STICK_PAD_MAX / 2)
		direction = DIR_UP;
	// X
	else if (values[0] < STICK_PAD_MIN / 2)
		direction = DIR_LEFT;
	else if (values[0] > STICK_PAD_MAX / 2)
		direction = DIR_RIGHT;
	
	if (direction != sc->direction) {
		sc->direction = direction;
		stick_controller_move(sc);
	}
}
