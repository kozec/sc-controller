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

/** Resets all virtual axes and virtual mouse position, all scheduled tasks, etc */
void testmapper_reset(Mapper* m);

/** Sets 'x' and 'y' to current mouse position. Either pointer may be NULL */
void testmapper_get_mouse_position(Mapper* _m, double* x, double* y);

/** Returns value stored for given axis */
AxisValue testmapper_get_axis_position(Mapper* _m, Axis axis);

/** Returns log of pressed keys. Returned string should not be deallocated by caller. */
const char* testmapper_get_keylog(Mapper* _m);

/** Returns number of currently pressed keys */
size_t testmapper_get_key_count(Mapper* _m);

/** Returns true if there are any tasks scheduled on test mapper */
bool testmapper_has_scheduled(Mapper* _m);

/**
 * Runs next task scheduled on test mapper.
 * Returns true if there are any more left.
 */
bool testmapper_run_scheduled(Mapper* _m, uint32_t time_delta);
