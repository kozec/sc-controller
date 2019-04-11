/**
 * Menu generator is .so with at least 'generate' function, which can dynamically
 * generate list of menu items.
 */

#pragma once
#ifdef __cplusplus
extern "C" {
#endif
#include "scc/utils/dll_export.h"
#include "scc/menu_data.h"
#include "scc/parameter.h"

typedef struct ParamDescription {
	ParameterType	type;
	const char*		description;
} ParamDescription;

typedef struct GeneratorContext GeneratorContext;
typedef struct Config Config;

struct GeneratorContext {
	/**
	 * Adds new menu item. Any of 'name', 'icon' and 'action' may be NULL.
	 * If 'action' is not NULL, this call steals one reference to it.
	 *
	 * Returns false if allocation fails, in which case reference is not stolen.
	 */
	bool (*add_action)(GeneratorContext* ctx, const char* name, const char* icon, Action* action);
	
	/**
	 * Returns config object.
	 * Returned object will be available at least until scc_menu_generator_get_items
	 * function is finished and so there should be no need to handle reference count on it.
	 */
	Config* (*get_config)(GeneratorContext* ctx);
	
	/**
	 * Returns parameter or NULL if index is out of range.
	 * Returned object will be available at least until scc_menu_generator_get_items
	 * function is finished and so there should be no need to handle reference count on it.
	 */
	Parameter* (*get_parameter)(GeneratorContext* ctx, size_t index);
};

/**
 * Generates list of menu items.
 * Generator should call one of scc_menu_generator_add* functions for every new
 * item.
 *
 * Returns array of menu items, while setting size_return to size of that array.
 */
typedef void (*scc_menu_generator_generate_fn)(GeneratorContext* ctx);

/**
 * Returns array of 'ParamDescription'. This is used by GUI to create generator configuration.
 * Returned array is _not_ deallocated by called.
 * Array has to be terminated by  { 0, NULL };
 *
 * May return NULL to indicate there are no parameters.
 */
typedef const ParamDescription* (*scc_menu_generator_get_parameters_fn)();

#ifdef __cplusplus
}
#endif

