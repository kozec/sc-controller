/**
 * SC Controller - Menu Data
 *
 * Container for list of menu items + related tools.
 *
 * MenuData is not reference-counted, but it holds reference-counted Actions.
 * That means until MenuData is deallocated, it' safe to assume that all
 * referenced Actions (and all MenuItems) are staying in memory as well.
 *
 * On other hand, once scc_menudata_free is called, all MenuItems stored in it
 * are freed as well.
 */
#pragma once
#include "scc/utils/list.h"
#include "scc/action.h"

typedef struct MenuData MenuData;
typedef struct MenuItem MenuItem;
typedef struct Config Config;

typedef enum {
	MI_SEPARATOR,
	MI_GENERATOR,
	MI_SUBMENU,
	MI_ACTION,
	MI_DUMMY,
} MenuItemType;


struct MenuItem {
	/** Item type */
	const MenuItemType		type;
	
	/**
	 * Unique identifier of menu item. No two menu items in menu file shall
	 * have same id.
	 * If no id is provided in json file, auto-generated one is assigned.
	 * But in such case, if item is not generator, separator or submenu,
	 * it's considered "dummy".
	 */
	const char*				id;
	
	/**
	 * Item name (label). May be NULL, in which case:
	 *   - For MI_ACTION, action description should be used, unless action is NULL as well.
	 *   - For MI_SUBMENU, submenu name should be used
	 *   - For MI_SEPARATOR, separator should have no label drawn
	 *   - For MI_GENERATOR, there is no name anyway
	 */
	const char*				name;
	
	union {
		/** Action to be executed. May be NULL. Available only with MI_ACTION */
		Action*				action;
		
		/**
		 * Generator name. If name is recognized, generator code is called
		 * to generate menu items. Available only with MI_GENERATOR
		 */
		const char*			generator;
		
		/** Name of menu file to load submenu from. Available only with MI_SUBMENU */
		const char*			submenu;
	};
	
	/** Name of icon displayed along with label */
	const char*				icon;
	
	/** Store anything needed here. OSD puts widget & callback here */
	void*					userdata;
};


struct MenuData {
	ListIterator (*iter_get)(MenuData* d);
};


/**
 * Errors codes set when NULL is returned:
 * - 1: Failed to open file
 * - 2: Failed to decode json data
 * - 3: JSON decoded, but not to expected format
 */
MenuData* scc_menudata_from_json(const char* filename, int* error);

/**
 * Errors codes set when NULL is returned:
 * - 0: Generator generated no data (not really error)
 * - 1: Unknown generator
 * - 2: Generator is known, but failed to be loaded
 * - 3: Parameters provided, but failed to parse
 * - 4: Out of memory
 */
MenuData* scc_menudata_from_generator(const char* generator, Config* config, int* error);

/**
 * Converts all MI_GENERATOR items into items they generated.
 * Returns 1 on success
 * Returns 0 if any generator failed.
 * Returns 4 on memory error.
 *
 * It's partially safe to ignore errors; MenuData will be changed
 * in some undefined way, but it will still contain valid menu.
 */
int scc_menudata_apply_generators(MenuData* data, Config* cfg);

/**
 * Returns menu item with matching id or NULL if there is no such.
 * Returned item shall not be deallocated - it will be alive
 * as long as parent MenuData is.
 */
MenuItem* scc_menudata_get_by_id(const MenuData* data, const char* id);

/** Returns menu item at given index or NULL if index is out of range */
MenuItem* scc_menudata_get_by_index(const MenuData* data, size_t index);

/** Returns number of items in menu */
size_t scc_menudata_len(const MenuData* data);



// TODO: Where t.f. is scc_menudata_free?

