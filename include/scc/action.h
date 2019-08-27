#pragma once
#include "scc/utils/rc.h"
#include "scc/parameter.h"
#include "scc/mapper.h"
#include "scc/error.h"
#include <stdbool.h>

typedef enum ActionFlags {
	// ActionFlags and ParameterType values has to be mutually exclusive,
	// with exception of AF_ERROR / PT_ERROR
	AF_NONE						= 0b0000,
	AF_ERROR					= 0b0001,
	AF_ACTION					= 0b000000000000001 << 9,
	AF_MODIFIER					= 0b000000000000010 << 9,
	AF_SPECIAL_ACTION			= 0b000000000000101 << 9,
	AF_AXIS						= 0b000000000001000 << 9,		// special in some cases
	AF_KEYCODE					= 0b000000000010000 << 9,		// action supports 'keycode' property which is used by OSD keyboard
	AF_MOD_CLICK				= 0b000000000100000 << 9,		// action supports 'clicked' modifier
	AF_MOD_OSD					= 0b000000001000000 << 9,		// action supports 'osd' modifier
	AF_MOD_FEEDBACK				= 0b000000010000000 << 9,		// ... et cetera. AF_MOD_* is used by GUI
	AF_MOD_DEADZONE				= 0b000000100000000 << 9,
	AF_MOD_SENSITIVITY			= 0b000001000000000 << 9,
	AF_MOD_SENS_Z				= 0b000010000000000 << 9,		// Sensitivity of 3rd axis
	AF_MOD_ROTATE				= 0b000100000000000 << 9,
	AF_MOD_POSITION				= 0b001000000000000 << 9,
	AF_MOD_SMOOTH				= 0b010000000000000 << 9,
	AF_MOD_BALL					= 0b100000000000000 << 9,
	ActionFlags_pad_			= 0xFFFFFFFF
} ActionFlags;

typedef enum ActionDescContext {
	AC_BUTTON	= 1 << 0,
	AC_STICK	= 1 << 2,
	AC_TRIGGER	= 1 << 3,
	AC_GYRO		= 1 << 4,
	AC_PAD		= 1 << 5,
	AC_OSD		= 1 << 8,
	AC_OSK		= 1 << 9,			// On screen keyboard
	AC_MENU		= 1 << 10,			// Menu Item
	AC_SWITCHER	= 1 << 11,			// Autoswitcher display
	AC_ALL		= 0b10111111111		// ALL means everything but OSK
} ActionDescContext;

typedef struct Action Action;
typedef LIST_TYPE(Action) ActionList;

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
	 * Action->to_string returns string that is situable for displaying in
	 * GUI, OSD, or on similar place. Contex is information about intended
	 * use of string.
	 *
	 * This method may be set to NULL. Use scc_action_get_description instead of
	 * callign it directly if you prefer having defaults provided instead of
	 * handling it.
	 *
	 * Returned string has to be free'd by caller. Returns NULL on OOM error.
	 */
	char*	(*describe)(Action* a, ActionDescContext ctx);
	
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
	 * 'accel_x', 'y' and 'z' fields in GyroInput represents change in position.
	 * 'pitch', 'yaw' and 'roll' represents change in gyroscope rotations.
	 * 'q1' to 'q4' represents absolute rotation expressed as quaterion.
	 */
	void	(*gyro)(Action* a, Mapper* m, const struct GyroInput* value);
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
	 * Returns named property of action. This is used mainly by tests and
	 * potetially by GUI and doesn't have to be implemented - defaults to method
	 * that return NULL for anything.
	 *
	 * If implemented, method should return Parameter* instance with one reference
	 * that caller has to release or NULL for unknown property names.
	 */
	Parameter*	(*get_property)(Action* a, const char* name);
	
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
		void		(*set_haptic)(Action* a, HapticData hdata);
		/**
		 * If action supports sensitivity, this method is called from
		 * SensitivityModifier. Otherwise, SensitivityModifier will not do anything.
		 */
		void		(*set_sensitivity)(Action* a, float x, float y, float z);
		/**
		 * 'change' is called on supported actions by BallModifier
		 */
		void		(*change)(Action* a, Mapper* m, double dx, double dy, PadStickTrigger what);
		/**
		 * For modifier, 'get_child' returns child action or NoAction if there is none.
		 * Caller has to dereference returned action.
		 */
		Action*		(*get_child)(Action* a);
		/**
		 * For dpad, 'and', macro and similar multiaction, returns list of child
		 * actions. Returned ActionList should hold references to each Actions in it.
		 */
		ActionList	(*get_children)(Action* a);
	} extended;
};


extern Action* NoAction;

typedef ActionOE(*scc_action_constructor)(const char* keyword, ParameterList params);

/**
 * Creates action list out of varargs.
 * Reference counter on added actions is properly increased and decreased
 * when ActionList is deallocated.
 * Returns NULL (and releases/deallocates everything) if allocation fails
 */
#define scc_make_action_list(...) _scc_make_action_list(__VA_ARGS__, NULL)
ActionList _scc_make_action_list(Action* list, ...);

/**
 * Creates copy of action list. Reference counts are properly increased
 * and decreased when ActionList is deallocated.
 *
 * Returns NULL if allocation fails.
 */
ActionList scc_copy_action_list(ActionList lst);


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

struct ModeshiftModes {
	Parameter*		mode;
	Action*			action;
};

/**
 * Returns tuple parameter containing list of modes and actions assotiated with
 * mode modifier. Each mode is represented by nested tuple containing
 * (condition, action). Condition may be button, range or None for default item.
 *
 * Returned value has to be dereferenced by called.
 * May return NULL if allocation fails.
 */
Parameter* scc_modeshift_get_modes(Action* a);

/** Returns true if action is NoAction */
bool scc_action_is_none(Action* a);

/**
 * Calls compress method on action to which *a points to and replaces *a target
 * with aciton it returns. Reference counters are properly decreased on old
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

/**
 * Returns string description of action, as should be displayed in GUI or in OSD.
 * 'ctx' contains information about intended use of string, but it can be NULL.
 * Returns NULL if space for generated string cannot be allocated.
 *
 * Returned string has to be freed by caller.
 */
char* scc_action_get_description(Action* a, ActionDescContext ctx);


/**
 * See get_property method on Action.
 * This wrappers just ensures that returned parameter is of expected type.
 * expected_type may be set to PT_ANY to skip this check.
 *
 * Returns NULL (while properly deallocating thrown-out parameter if needed)
 */
Parameter* scc_action_get_property_with_type(Action* a, const char* name, ParameterType expected_type);

