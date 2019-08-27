/**
 * SC Controller - Daemon - locking
 *
 * Locking in this context means 'locking button by client'. Inputs from locked
 * button (or stick, pad, etc) are temporaly disabled and sent to client that
 * locked them instead.
 *
 * This is used by OSD to get controller inputs without taking device away from
 * game.
 */
 
#define LOG_TAG "Daemon"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/profile.h"
#include "scc/action.h"
#include "scc/tools.h"
#include "daemon.h"
#include <stdlib.h>

static const char* PROFILE_TYPE_LOCK = "LockProfile";
#define MIN_DIFFERENCE 300
typedef enum {
	/**
	 * Source is locking-specific list of things that client can request lock for.
	 * It may look like SCButton enum, but it's not.
	 */
	// Buttons & pads
	SRC_LPADTOUCH,
	SRC_RPADTOUCH,
	SRC_LPADPRESS,
	SRC_RPADPRESS,
	SRC_LGRIP,
	SRC_RGRIP,
	SRC_START,
	SRC_C,
	SRC_BACK,
	SRC_A,
	SRC_X,
	SRC_B,
	SRC_Y,
	SRC_LB,
	SRC_RB,
	SRC_CPADTOUCH,
	SRC_CPADPRESS,
	SRC_STICKPRESS,
	// Triggers (LT/RT cannot be locked as button)
	SRC_LTRIGGER,
	SRC_RTRIGGER,
	// Stick & pad
	SRC_STICK,
	SRC_LPAD,
	SRC_RPAD,
	SRC_CPAD,
	
	SRC_MAX,
	SRC_INVALID,
} Source;

typedef struct {
	Action			action;
	Source			source;
	AxisValue		old_x, old_y;
	Client*			owner;
} LockedAction;

typedef struct {
	/**
	 * LockProfile is 'proxy profile' that redirect everything locked to its
	 * own, reporting implementation and everything else to original profile
	 */
	Profile			profile;
	Profile*		original;
	LockedAction	actions[SRC_MAX];
} LockProfile;


/**
 * Converts source as string to source as enum value or SRC_INVALID if
 * string is not recognized
 */
static Source string_to_source(const char* source) {
	switch (source[0]) {
	case 'R':
		if (0 == strcmp("RB", source)) return SRC_RB;
		if (0 == strcmp("RGRIP", source)) return SRC_RGRIP;
		if (0 == strcmp("RPAD", source)) return SRC_RPADPRESS;
		if (0 == strcmp("RPADPRESS", source)) return SRC_RPAD;
		if (0 == strcmp("RTRIGGER", source)) return SRC_RTRIGGER;
		if (0 == strcmp("RPADTOUCH", source)) return SRC_RPADTOUCH;
		break;
	case 'L':
		if (0 == strcmp("LB", source)) return SRC_LB;
		if (0 == strcmp("LPAD", source)) return SRC_LPAD;
		if (0 == strcmp("LGRIP", source)) return SRC_LGRIP;
		if (0 == strcmp("LTRIGGER", source)) return SRC_LTRIGGER;
		if (0 == strcmp("LPADPRESS", source)) return SRC_LPADPRESS;
		if (0 == strcmp("LPADTOUCH", source)) return SRC_LPADTOUCH;
		break;
	case 'S':
		if (0 == strcmp("START", source)) return SRC_START;
		if (0 == strcmp("STICK", source)) return SRC_STICK;
		if (0 == strcmp("STICKPRESS", source)) return SRC_STICKPRESS;
		break;
	case 'C':
		if (0 == strcmp("C", source)) return SRC_C;
		if (0 == strcmp("CPADTOUCH", source)) return SRC_CPADTOUCH;
		if (0 == strcmp("CPADPRESS", source)) return SRC_CPADPRESS;
		break;
	case 'B':
		if (0 == strcmp("B", source)) return SRC_B;
		if (0 == strcmp("BACK", source)) return SRC_BACK;
		break;
	default:
		if (0 == strcmp("A", source)) return SRC_A;
		if (0 == strcmp("X", source)) return SRC_X;
		if (0 == strcmp("Y", source)) return SRC_Y;
	}
	
	return SRC_INVALID;
}

/** Opposite or string_to_source */
static const char* source_to_string[] = {
	"LPADTOUCH", "RPADTOUCH", "LPADPRESS", "RPADPRESS", "RGRIP", "LGRIP",
	"START", "C", "BACK", "A", "X", "B", "Y", "LB", "RB", "CPADTOUCH",
	"CPADPRESS", "STICKPRESS", "LTRIGGER", "RTRIGGER", "STICK",
	"LPAD", "RPAD", "CPAD"
};

/** Converts SCButton value to Source value */
static Source scbutton_to_source(SCButton b) {
	switch (b) {
		case B_RPADTOUCH:	return SRC_RPADTOUCH;
		case B_LPADTOUCH:	return SRC_LPADTOUCH;
		case B_RPADPRESS:	return SRC_RPADPRESS;
		case B_LPADPRESS:	return SRC_LPADPRESS;
		case B_RGRIP:		return SRC_RGRIP;
		case B_LGRIP:		return SRC_LGRIP;
		case B_START:		return SRC_START;
		case B_C:			return SRC_C;
		case B_BACK:		return SRC_BACK;
		case B_A:			return SRC_A;
		case B_X:			return SRC_X;
		case B_B:			return SRC_B;
		case B_Y:			return SRC_Y;
		case B_LB:			return SRC_LB;
		case B_RB:			return SRC_RB;
		// case B_LT:		// not used
		// case B_RT:		// not used
		case B_CPADTOUCH:	return SRC_CPADTOUCH;
		case B_CPADPRESS:	return SRC_CPADPRESS;
		case B_STICKPRESS:	return SRC_STICKPRESS;
		default:
			break;
	}
	
	return SRC_INVALID;
}

/** Converts PadStickTrigger value to Source value */
static Source what_to_source(PadStickTrigger what) {
	switch (what) {
		case PST_LPAD:		return SRC_LPAD;
		case PST_RPAD:		return SRC_RPAD;
		case PST_LTRIGGER:	return SRC_LTRIGGER;
		case PST_RTRIGGER:	return SRC_RTRIGGER;
		case PST_CPAD:		return SRC_CPAD;
		case PST_STICK:		return SRC_STICK;
		case PST_GYRO:
			break;
	}
	return SRC_INVALID;
}


static void locked_profile_dealloc(void* obj) {
	LockProfile* p = container_of(obj, LockProfile, profile);
	RC_REL(p->original);
	free(p);
}

static Action* locked_profile_get_button(Profile* _p, SCButton b) {
	LockProfile* p = container_of(_p, LockProfile, profile);
	Source src = scbutton_to_source(b);
	if ((src != SRC_INVALID) && (p->actions[src].owner != NULL))
		return &p->actions[src].action;
	return p->original->get_button(p->original, b);
}

static Action* locked_profile_get_trigger(Profile* _p, PadStickTrigger what) {
	LockProfile* p = container_of(_p, LockProfile, profile);
	Source src = what_to_source(what);
	if ((src != SRC_INVALID) && (p->actions[src].owner != NULL)) {
		return &p->actions[src].action;
	}
	return p->original->get_trigger(p->original, what);
}

static Action* locked_profile_get_pad(Profile* _p, PadStickTrigger what) {
	LockProfile* p = container_of(_p, LockProfile, profile);
	Source src = what_to_source(what);
	if ((src != SRC_INVALID) && (p->actions[src].owner != NULL))
		return &p->actions[src].action;
	return p->original->get_pad(p->original, what);
}

static Action* locked_profile_get_stick(Profile* _p) {
	LockProfile* p = container_of(_p, LockProfile, profile);
	if (p->actions[SRC_STICK].owner != NULL) {
		return &p->actions[SRC_STICK].action;
	}
	return p->original->get_stick(p->original);
}

static Action* locked_profile_get_gyro(Profile* _p) {
	// Gyro is not lockable
	LockProfile* p = container_of(_p, LockProfile, profile);
	return p->original->get_gyro(p->original);
}

bool sccd_is_locked_profile(Profile* p) {
	return 0 == strcmp("LockProfile", p->type);
}

void sccd_change_locked_profile(Profile* _p, Profile* child) {
	ASSERT(sccd_is_locked_profile(_p));
	LockProfile* p = container_of(_p, LockProfile, profile);
	RC_REL(p->original);
	p->original = child;
	RC_ADD(p->original);
}

static char* locked_action_to_string(Action* a) {
	return strbuilder_cpy("<locked_action>");
}

static void lock_action_button_press(Action* _a, Mapper *m) {
	LockedAction* a = container_of(_a, LockedAction, action);
	Controller* c = m->get_controller(m);
	char* message = strbuilder_fmt("Event: %s %s 1\n", c->get_id(c), source_to_string[a->source]);
	if (message == NULL)
		sccd_drop_client_asap(a->owner);
	else
		sccd_socket_consume(a->owner, message);
}

static void lock_action_whole(Action* _a, Mapper* m, AxisValue x, AxisValue y, PadStickTrigger what) {
	// TODO: Check MIN_DIFFERENCE
	LockedAction* a = container_of(_a, LockedAction, action);
	if ((x == 0) || (abs(x - a->old_x) > MIN_DIFFERENCE) || (y == 0) || (abs(y - a->old_y) > MIN_DIFFERENCE)) {
		a->old_x = x; a->old_y = y;
		
		Controller* c = m->get_controller(m);
		char* message = strbuilder_fmt("Event: %s %s %i %i\n", c->get_id(c), scc_what_to_string(what), x, y);
		if (message == NULL)
			sccd_drop_client_asap(a->owner);
		else
			sccd_socket_consume(a->owner, message);
	}
}

static void lock_action_trigger(Action* _a, Mapper* m, TriggerValue old_pos, TriggerValue pos, PadStickTrigger what) {
	LockedAction* a = container_of(_a, LockedAction, action);
	Controller* c = m->get_controller(m);
	char* message = strbuilder_fmt("Event: %s %s %i %i\n", c->get_id(c), scc_what_to_string(what), pos, old_pos);
	if (message == NULL)
		sccd_drop_client_asap(a->owner);
	else
		sccd_socket_consume(a->owner, message);
}

static void lock_action_button_release(Action* _a, Mapper *m) {
	LockedAction* a = container_of(_a, LockedAction, action);
	Controller* c = m->get_controller(m);
	char* message = strbuilder_fmt("Event: %s %s 0\n", c->get_id(c), source_to_string[a->source]);
	if (message == NULL)
		sccd_drop_client_asap(a->owner);
	else
		sccd_socket_consume(a->owner, message);
}

/**
 * Tests if LockProfile is in place and if it's still needed.
 * if there are no locked actions left, deallocates LockProfile
 * and sets original profile back in place
 */
inline static void maybe_cancel_lock_profile(Client* c, LockProfile* lp) {
	for (Source src=0; src<SRC_MAX; src++) {
		if (lp->actions[src].owner != NULL)
			// Something's still locked, bail out
			return;
	}
	
	c->mapper->set_profile(c->mapper, lp->original, false);
	RC_REL(&lp->profile);
}


const char* sccd_lock_actions(Client* c, StringList sources) {
	if (list_len(sources) == 0)
		// Sucesfully locked nothing
		return NULL;
	
	ListIterator it = iter_get(sources);
	if (it == NULL)
		return SCCD_OOM;
	
	Profile* profile = c->mapper->get_profile(c->mapper);
	if (profile->type != PROFILE_TYPE_LOCK) {
		// There was no input locked yet, I have to establish LockProfile 1st
		LockProfile* lp = malloc(sizeof(LockProfile));
		if (lp == NULL) {
			iter_free(it);
			return SCCD_OOM;
		}
		RC_INIT(&lp->profile, &locked_profile_dealloc);
		lp->original = profile;
		RC_ADD(lp->original);
		for (Source src=0; src<SRC_MAX; src++) {
			scc_action_init(&lp->actions[src].action, PROFILE_TYPE_LOCK, AF_ACTION, NULL, &locked_action_to_string);
			RC_STATIC(&lp->actions[src].action);
			lp->actions[src].source = src;
			lp->actions[src].owner = NULL;
			lp->actions[src].old_x = 0;
			lp->actions[src].old_y = 0;
			lp->actions[src].action.whole = &lock_action_whole;
			lp->actions[src].action.trigger = &lock_action_trigger;
			lp->actions[src].action.button_press = &lock_action_button_press;
			lp->actions[src].action.button_release = &lock_action_button_release;
		}
		lp->profile.type = PROFILE_TYPE_LOCK;
		lp->profile.get_button = &locked_profile_get_button;
		lp->profile.get_trigger = &locked_profile_get_trigger;
		lp->profile.get_pad = &locked_profile_get_pad;
		lp->profile.get_stick = &locked_profile_get_stick;
		lp->profile.get_gyro = &locked_profile_get_gyro;
		
		profile = &lp->profile;
		c->mapper->set_profile(c->mapper, profile, false);
	}
	
	LockProfile* lp = container_of(profile, LockProfile, profile);
	// Check if all actions are available for locking
	FOREACH(const char*, source, it) {
		Source src = string_to_source(source);
		if ((src == SRC_INVALID) || (lp->actions[src].owner != NULL)) {
			if (src == SRC_INVALID)
				WARN("Client requested to lock '%s', I have no idea what that is", source);
			maybe_cancel_lock_profile(c, lp);
			iter_free(it);
			return source;
		}
	}
	
	// Performs actual locking
	iter_reset(it);
	Controller* controller = c->mapper->get_controller(c->mapper);
	FOREACH(const char*, source, it) {
		Source src = string_to_source(source);
		lp->actions[src].owner = c;
		DDEBUG("Source %i/%s locked on %s by client %p", src, source, controller->get_description(controller), c);
	}	
	
	iter_free(it);
	return NULL;
}

void sccd_unlock_actions(Client* c) {
	Profile* profile = c->mapper->get_profile(c->mapper);
	if (profile->type != PROFILE_TYPE_LOCK)
		// Unlocking not needed
		return;
	LockProfile* lp = container_of(profile, LockProfile, profile);
	for (Source src=0; src<SRC_MAX; src++) {
		if (lp->actions[src].owner == c)
			lp->actions[src].owner = NULL;
	}
	maybe_cancel_lock_profile(c, lp);
}

