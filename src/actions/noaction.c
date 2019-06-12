#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/action.h"
#include <stdlib.h>
#include <stdio.h>

static Action _noaction;
static const char* KW_NONE = "None";
Action* NoAction = NULL;


static char* noaction_to_string(Action* _button) {
	return strbuilder_cpy(KW_NONE);
}

static ActionOE noaction_constructor(const char* keyword, ParameterList params) {
	return (ActionOE)NoAction;
}


static void noaction_button_press(Action* a, Mapper* m) { }

static void noaction_button_release(Action* a, Mapper* m) { }

static void noaction_axis(Action* a, Mapper* m, AxisValue value, PadStickTrigger what) { }

static void noaction_gyro(Action* a, Mapper* m, const struct GyroInput* value) { }

static void noaction_whole(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) { }

static void noaction_trigger(Action* a, Mapper* m, TriggerValue old_pos,
					TriggerValue pos, PadStickTrigger what) { }

static char* noaction_describe(Action* a, ActionDescContext ctx) {
	return strbuilder_cpy("(not set)");
}

void scc_actions_init_noaction() {
	if (NoAction == NULL) {
		NoAction = (Action*)&_noaction;
		
		scc_action_init(NoAction, KW_NONE, AF_NONE, NULL, noaction_to_string);
		NoAction->describe = &noaction_describe;
		NoAction->button_press = &noaction_button_press;
		NoAction->button_release = &noaction_button_release;
		NoAction->axis = &noaction_axis;
		NoAction->gyro = &noaction_gyro;
		NoAction->whole = &noaction_whole;
		NoAction->trigger = &noaction_trigger;
		
		scc_action_register(KW_NONE, &noaction_constructor);
	}
}

