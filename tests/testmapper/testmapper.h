/*
 * SC Controller - Test Mapper
 *
 * Fake mapper used by tests. Instead of emulating anything it remembers what it
 * was supposed to do and allows tests to check results.
 */
#pragma once
#include "scc/controller.h"
#include "scc/mapper.h"

Mapper* testmapper_new();
void testmapper_free(Mapper* m);

/** Sets current state of buttons. Previos state is remembered for use of was_* methods */
void testmapper_set_buttons(Mapper* m, SCButton buttons);

/** Resets all virtual axes and virtual mouse position */
void testmapper_reset(Mapper* m);

/** Sets 'x' and 'y' to current mouse position. Either pointer may be NULL */
void testmapper_get_mouse_position(Mapper* _m, double* x, double* y);

/** Returns value stored for given axis */
AxisValue testmapper_get_axis_position(Mapper* _m, Axis axis);
