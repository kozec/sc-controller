#pragma once
#include "scc/utils/rc.h"
#include "scc/parameter.h"
#include "scc/mapper.h"
#include "scc/error.h"
#include <stdbool.h>

typedef enum ActionFlags {
	// ActionFlags and ParameterType values has to be mutually exclusive,
	// with exception of AF_ERROR / PT_ERROR
	AF_NONE						= 0b00000000000000,
	AF_ERROR					= 0b00000000000001,
	AF_ACTION					= 0b00001 << 8,
	AF_MODIFIER					= 0b00010 << 8,
	AF_SPECIAL_ACTION			= 0b00100 << 8,
	AF_AXIS						= 0b01000 << 8,	// special in some cases
	ActionFlags_pad_			= 0xFFFF
} ActionFlags;

typedef struct Action Action;

// Action, Parameter, ActionError and ParamError begins with same header
// and both ParameterType and ActionFlags have value 1 reserved for error.
// 
// This is done this way so type of returned pointer can be determined simply
// by casting it to (unsigned short*) and comparing to 1.
// Only error vs Parameter and error vs Action is interesting check,
// there should be no way to return Action where Parameter is expected.

struct Action {
	ActionFlags				flags;
	RC_HEADER;
	
	/**
	 * Set to type of action. String constant used internally as form of type check
	 * 'type' on two Actions of same type should point to same value, so it can
	 * be sucesfully compared not only with strmp, but also using ==.
	 */
	const char*		type;
	
	/** 
	 * Action->to_string returns string that can be parsed back to same action.
	 * This is used when serializing or letting user to edit action with
	 * Custom Action Editor in GUI.
	 *
	 * Returned string has to be free'd by caller. Returns NULL on OOM error.
	 */
	char*	(*to_string)(Action* a);
	
	/**
	 * Called when action is executed by pressing physical gamepad button.
	 * It's guaranteed that ButtonRelease will be called later.
	 */
	void	(*button_press)(Action* a, Mapper* m);
	/**
	 * Called when action executed by pressing physical gamepad button is
	 * expected to stop.
	 */
	void	(*button_release)(Action* a, Mapper* m);
	/**
	 * Called by XYAction to execute one of two actions defined for different
	 * axes of same pad / stick.
	 *
	 * 'what' is one of LEFT, RIGHT or STICK, describing what is being updated
	 */
	void	(*axis)(Action* a, Mapper* m, AxisValue value, PadStickTrigger what);
	/**
	 * Called when action is set by rotating gyroscope.
	 * 'pitch', 'yaw' and 'roll' represents change in gyroscope rotations.
	 * 'q1' to 'q4' represents absolute rotation expressed as quaterion.
	 */
	void	(*gyro)(Action* a, Mapper* m, GyroValue pitch, GyroValue yaw, GyroValue roll,
						GyroValue q1, GyroValue q2, GyroValue q3, GyroValue q4);
	/**
	 * Called when action is executed by moving physical stick or touching
	 * physical pad, when one action is defined for whole pad or stick.
	 * 
	 * 'x' and 'y' contains current stick or finger position.
	 * 'what' is one of LEFT, RIGHT or STICK, describing what is being updated
	 */
	void	(*whole)(Action* a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what);
	/**
	 * Called when action is executed by pressing (or releasing) physical
	 * trigger.
	 * 
	 * 'old_pos' is last known trigger position.
	 * 'pos' is current trigger position.
	 */
	void	(*trigger)(Action* a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what);
	
	/**
	 * compress() is called automatically on every action laoded from profile.
	 * 
	 * For modifier that's not needed for execution (such as NameModifier
	 * or SensitivityModifier that already applied its settings), it should
	 * return child action, without touching reference count of it or of itself.
	 * For anything else, compress method should return itself.
	 * 
	 * When called on action that contains other child action, parent aciton
	 * should ensure that Compress is called on all child actions and those
	 * child actions are replaced by results if needed.
	 *
	 * Also see scc_action_compress.
	 */
	Action*	(*compress)(Action* a);
	
	/**
	 * ExtendedMethods are methods that most of actions _don't_ have, and
	 * so there would be no point in polluting 'struct Action' with them.
	 *
	 * Extended contains size and so it may be extended at later time, as long
	 * as layout of Action struct (up to extended.size) stays the same.
	 */
	struct {
		size_t size;
		/**
		 * If action supports handling haptic effects, this method is called from
		 * FeedbackModifier to set effect to be used.
		 */
		void	(*set_haptic)(Action* a, HapticData hdata);
		/**
		 * If action supports sensitivity, this method is called from
		 * SensitivityModifier. Otherwise, SensitivityModifier will not do anything.
		 */
		void	(*set_sensitivity)(Action* a, float x, float y, float z);
		/**
		 * 'change' is called on supported actions by BallModifier
		 */
		void	(*change)(Action* a, Mapper* m, double dx, double dy, PadStickTrigger what);
	} extended;
};


Action* NoAction;

typedef ActionOE(*scc_action_constructor)(const char* keyword, ParameterList params);

void scc_action_register(const char* keyword, scc_action_constructor constructor);
/** Initializes Action struct, setting everything not given as argument to NULL */
void scc_action_init(Action* a, const char* type, ActionFlags flags,
		void(*dealloc)(Action* a), char*(*to_string)(Action* a));

/** Returns true if there is action registered for given keyword */
bool scc_action_known(const char* keyword);

/** Creates new action using given keyword and parameters */
ActionOE scc_action_new(const char* keyword, ParameterList params);
/** Returns NULL if memory cannot be allocated */
Action* scc_button_action_from_keycode(unsigned short keycode);
/** Creates new Macro. Returns NULL if memory cannot be allocated. */
Action* scc_macro_new(Action** actions, size_t action_count);
/**
 * Combines two actions into Macro. If either (or both) already are Macro,
 * new Macro will contain combination of actions from them, but not macros themselves.
 * Returns NULL if memory cannot be allocated.
 */
Action* scc_macro_combine(Action* a1, Action* a2);
/**
 * Appends action to Macro. This modifies Macro in place and increases reference
 * count on 'a' on success.
 * There are two rules to this:
 *  - action 'm' (one being modified) has to be a macro
 *  - action 'a' has to be anything but macro
 * Returns false if memory cannot be allocated or if called with wrong arguments.
 */
bool scc_macro_add_action(Action* m, Action* a);
/** Creates new Multiaction ("and"). Returns NULL if memory cannot be allocated. */
Action* scc_multiaction_new(Action** actions, size_t action_count);
/**
 * Combines two actions into Multiaction. If either (or both) already are Multiaction,
 * new Multiaction will contain combination of actions from them,
 * but not multiactions themselves.
 * Returns NULL if memory cannot be allocated.
 */
Action* scc_multiaction_combine(Action* a1, Action* a2);


/**
 * Calls compress method on action to which *a points to and replaces *a target
 * with aciton it returns. Reference cointers are properly decreased on old
 * and increased on new target or 'a'.
 *
 * Returns true if value of *a was changed.
 *
 * If a is NULL, points to NULL, or action it points to doesn't have compress
 * method defined, function does nothing and returns false.
 */
bool scc_action_compress(Action** a);
/**
 * Returns string representation of action, same or equivalent to one that parser
 * used to construct this action in 1st place.
 * Returns NULL if space for generated string cannot be allocated.
 *
 * Returned string has to be freed by caller.
 */
char* scc_action_to_string(Action* a);
