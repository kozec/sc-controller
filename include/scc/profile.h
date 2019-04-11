/*
 * SC Controller - Profile
 * 
 * Profile is collection of actions, preferably stored in file.
 */
#pragma once
#include "scc/utils/rc.h"
#include "scc/controller.h"
#include "scc/action.h"

typedef struct Profile Profile;

struct Profile {
	RC_HEADER;
	
	/**
	 * Set to type of profile. String constant used internally as form of type check
	 * 'type' on two Profiles of same type should point to same value, so it can
	 * be sucesfully compared not only with strmp, but also using ==.
	 */
	const char*		type;
	
	/**
	 * Returns action assigned to given button or NoAction.
	 * Reference counter on returned action is increased and has to be 
	 * decreased by caller unless it's NoAction, in which case reference counter
	 * is ignored (but it's safe to decrease.)
	 */
	Action*			(*get_button)(Profile* p, SCButton b);
	
	/**
	 * Returns action assigned to given trigger or NoAction.
	 * Reference counter on returned action is increased and has to be 
	 * decreased by caller unless it's NoAction, in which case reference counter
	 * is ignored (but it's safe to decrease.)
	 */
	Action*			(*get_trigger)(Profile* p, PadStickTrigger t);
	
	/**
	 * Returns action assigned to given pad or NoAction.
	 * Reference counter on returned action is increased and has to be 
	 * decreased by caller unless it's NoAction, in which case reference counter
	 * is ignored (but it's safe to decrease.)
	 */
	Action*			(*get_pad)(Profile* p, PadStickTrigger t);
	
	/**
	 * Returns action assigned to stick (which can be NoAction).
	 * Reference counter on returned action is increased and has to be 
	 * decreased by caller unless it's NoAction, in which case reference counter
	 * is ignored (but it's safe to decrease.)
	 */
	
	Action*			(*get_stick)(Profile* p);
	
	/**
	 * Returns action assigned to gyros (which can be NoAction).
	 * Reference counter on returned action is increased and has to be 
	 * decreased by caller unless it's NoAction, in which case reference counter
	 * is ignored (but it's safe to decrease.)
	 */
	
	Action*			(*get_gyro)(Profile* p);
	
	bool			(*is_template)(Profile* p);
	float			(*get_version)(Profile* p);
	
	/** See compress method on action */
	void			(*compress)(Profile* p);
	// TODO: Menus
	// Menus()							Action
};


/**
 * Loads profile from json file.
 * If profile cannot be readed (file doesn't exists, it's not valid JSON file or
 * memory cannot be allocated), returns NULL. Otherwise, returns Profile with
 * reference that caller has to release.
 *
 * If function fails and error pointer is provided, it's set to one of following:
 *  - 0 - out of memory
 *  - 1 - failed to open the file
 *  - 2 - failed to decode JSON data
 *  - 3 - failed to decode profile (valid JSON, but not describing profile)
 */
Profile* scc_profile_from_json(const char* filename, int* error);

/** Generates new empty profile. This may return NULL only if there is no memory */
Profile* scc_make_empty_profile();

