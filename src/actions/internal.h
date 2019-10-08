/**
 * SC-Controller - Action internals.
 * Basically stuff that's neeeded in multiple c files at once.
 */

extern const char* KW_BALL;
extern const char* KW_GYROABS;


/** Replaces child action. Used by deadzone modifier. */
void scc_ball_replace_child(Action* a, Action* new_child);

/** Sets deadzone function used directly by gyroabs */
void scc_gyroabs_set_deadzone_mod(Action* a, Action* deadzone);

/** Applies deadzone to given axis value */
void scc_deadzone_apply(Action* a, AxisValue* value);

/** Returns value clamped between min/max allowed for axis */
AxisValue clamp_axis(Axis axis, double value);

