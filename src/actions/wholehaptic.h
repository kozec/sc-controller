/*
 * SC-Controller - WholeHapticAction
 *
 * Helper methods for actions that are generating haptic 'rolling clicks' as
 * user moves finger over pad.
 * This includes MouseAction, CircularModifier, XYAction and BallModifier.
 */
#pragma once
#include "scc/utils/container_of.h"
#include "scc/utils/math.h"
#include "scc/controller.h"
#include "scc/mapper.h"
#include <math.h>


typedef struct {
	HapticData		hdata;
	dvec_t			a;
} WholeHapticData;

#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wunused-function"


static inline void wholehaptic_reset(WholeHapticData* w) {
	w->a.x = w->a.y = 0;
}

static inline void wholehaptic_init(WholeHapticData* w) {
	wholehaptic_reset(w);
	HAPTIC_DISABLE(&w->hdata);
}

static void wholehaptic_change(WholeHapticData* w, Mapper* m, double dx, double dy) {
	if (HAPTIC_ENABLED(&w->hdata)) {
		w->a.x += dx;
		w->a.y += dy;
		
		double distance = dvec_len(w->a);
		if (distance > w->hdata.frequency) {
			wholehaptic_reset(w);
			m->haptic_effect(m, &w->hdata);
		}
	}
}

#pragma GCC diagnostic pop

#define WHOLEHAPTIC_MAKE_SET_HAPTIC(ActionType, wh_field)		\
	static void set_haptic(Action* _a, HapticData hdata) {		\
		ActionType* a = container_of(_a, ActionType, action);	\
		(wh_field).hdata = hdata;								\
	}
