#include "scc/utils/strbuilder.h"
#include "scc/action.h"
#include <stdlib.h>
#include <stdio.h>

static Action _noaction;
static const char* KW_NONE = "None";


static char* noaction_to_string(Action* _button) {
	return strbuilder_cpy(KW_NONE);
}

static ActionOE noaction_constructor(const char* keyword, ParameterList params) {
	return (ActionOE)NoAction;
}


void noaction_button_press(Action* a, Mapper* m) { }

void noaction_button_release(Action* a, Mapper* m) { }

void noaction_axis(Action* a, Mapper* m, AxisValue value, PadStickTrigger what) { }

void noaction_gyro(Action* a, Mapper* m, GyroValue pitch, GyroValue yaw, GyroValue roll,
					GyroValue q1, GyroValue q2, GyroValue q3, GyroValue q4) { }

void noaction_whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) { }

void noaction_trigger(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) { }

void scc_actions_init_noaction() {
	if (NoAction == NULL) {
		NoAction = (Action*)&_noaction;
		
		scc_action_init(NoAction, KW_NONE, AF_NONE, NULL, noaction_to_string);
		NoAction->button_press = &noaction_button_press;
		NoAction->button_release = &noaction_button_release;
		NoAction->axis = &noaction_axis;
		NoAction->gyro = &noaction_gyro;
		NoAction->whole = &noaction_whole;
		NoAction->trigger = &noaction_trigger;
		
		scc_action_register(KW_NONE, &noaction_constructor);
	}
}
