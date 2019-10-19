#define LOG_TAG "menu_data.c"
#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/tokenizer.h"
#include "scc/utils/iterable.h"
#include "scc/utils/aojls.h"
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/menu_data.h"
#include "scc/action.h"
#include "scc/parser.h"
#include "parser.h"
#include <unistd.h>
#include <stdlib.h>
#include <errno.h>

#if MENU_GENERATORS_ENABLED
#include "scc/tools.h"
#ifdef _WIN32
#include <windows.h>
#define FILENAME_PREFIX "libscc-menugen-"
#define FILENAME_SUFFIX ".dll"
#else
#include <dlfcn.h>
#define FILENAME_PREFIX "libscc-menugen-"
#define FILENAME_SUFFIX ".so"
#endif
#include "scc/menu_generator.h"
#endif

typedef LIST_TYPE(MenuItem) MItemList;

struct _MenuData {
	MenuData		menudata;
	MItemList		items;
};

long json_reader_fn(char* buffer, size_t len, void* reader_data);

static MenuItem* menuitem_new(MenuItemType t) {
	MenuItem* i = malloc(sizeof(MenuItem));
	memset(i, 0, sizeof(MenuItem));
	*(MenuItemType*)&i->type = t;
	return i;
}

static void menuitem_free(MenuItem* i) {
	if (i->id != NULL) free((char*)i->id);
	if (i->name != NULL) free((char*)i->name);
	if (i->icon != NULL) free((char*)i->icon);
	
	switch (i->type) {
	case MI_ACTION:
	case MI_DUMMY:
		if (i->action != NULL) RC_REL(i->action);
		break;
	case MI_SEPARATOR:
		break;
	case MI_SUBMENU:
		if (i->submenu != NULL) free((char*)i->submenu);
		break;
	case MI_GENERATOR:
		if (i->generator != NULL) free((char*)i->generator);
		break;
	}
	free(i);
}

void scc_menudata_free(MenuData* _dt) {
	struct _MenuData* dt = container_of(_dt, struct _MenuData, menudata);
	// TODO: Deallocate items
	list_free(dt->items);
	free(dt);
}


size_t scc_menudata_len(const MenuData* _dt) {
	struct _MenuData* dt = container_of(_dt, struct _MenuData, menudata);
	return list_len(dt->items);
}

MenuItem* scc_menudata_get_by_index(const MenuData* _dt, size_t index) {
	struct _MenuData* dt = container_of(_dt, struct _MenuData, menudata);
	size_t len = list_len(dt->items);
	if (index >= len)
		return NULL;
	return list_get(dt->items, index);
}

MenuItem* scc_menudata_get_by_id(const MenuData* _dt, const char* id) {
	struct _MenuData* dt = container_of(_dt, struct _MenuData, menudata);
	ListIterator it = iter_get(dt->items);
	FOREACH(MenuItem*, i, it) {
		if ((i->id != NULL) && (strcmp(i->id, id) == 0)) {
			// Already used
			iter_free(it);
			return i;
		}
	}
	iter_free(it);
	return NULL;
}


static ListIterator menudata_iter_get(MenuData* _dt) {
	struct _MenuData* dt = container_of(_dt, struct _MenuData, menudata);
	return iter_get(dt->items);
}


MenuData* scc_menudata_from_json(const char* filename, int* error) {
	MenuItem* it = NULL;
	struct _MenuData* dt = NULL;
	unsigned int next_auto_id = 1;
	// Open file
	FILE* fp = fopen(filename, "r");
	if (fp == NULL) {
		LERROR("Failed to open '%s': %s", filename, strerror(errno));
		if (error != NULL) *error = 1;
		return NULL;
	}
	
	// Parse JSON
	aojls_ctx_t* ctx;
	aojls_deserialization_prefs prefs = {
		.reader = &json_reader_fn,
		.reader_data = (void*)fp
	};
	ctx = aojls_deserialize(NULL, 0, &prefs);
	fclose(fp);
	if ((ctx == NULL) || (prefs.error != NULL)) {
		LERROR("Failed to decode '%s': %s", filename, prefs.error);
		if (error != NULL) *error = 2;
		json_free_context(ctx);
		return NULL;
	}
	
	json_array* root = json_as_array(json_context_get_result(ctx));
	if (root == NULL) {
		LERROR("Failed to decode '%s': root is not json array", filename);
		if (error != NULL) *error = 3;
		goto scc_menudata_from_json_invalid;
	}
	
	dt = malloc(sizeof(struct _MenuData));
	if (dt == NULL) goto scc_menudata_from_json_oom;
	dt->menudata.iter_get = &menudata_iter_get;
	dt->items = list_new(MenuItem, 0);
	if (dt->items == NULL) {
		free(dt);
		dt = NULL;
		goto scc_menudata_from_json_oom;
	}
	
	for (size_t i=0; i<json_array_size(root); i++) {
		json_object* item = json_array_get_object(root, i);
		if (item == NULL) {
			LERROR("Failed to decode '%s': %li-th item is not an object", filename, i);
			if (error != NULL) *error = 4;
			goto scc_menudata_from_json_invalid;
		}
		
		#define SET_FROM_JSON(what)											\
			const char* what = json_object_get_string(item, #what);			\
			if (what != NULL) {												\
				it->what = strbuilder_cpy(what);							\
				if (it->what == NULL) goto scc_menudata_from_json_oom;		\
			}
		
		if (json_object_get_bool(item, "separator", NULL)) {
			// Separator
			it = menuitem_new(MI_SEPARATOR);
		} else if (json_object_get_string(item, "generator") != NULL) {
			// Genrator
			it = menuitem_new(MI_GENERATOR);
			SET_FROM_JSON(generator);
		} else if (json_object_get_string(item, "submenu") != NULL) {
			// Genrator
			it = menuitem_new(MI_SUBMENU);
			SET_FROM_JSON(submenu);
		} else {
			it = menuitem_new(MI_ACTION);
			if (it == NULL) goto scc_menudata_from_json_oom;
		}
		
		SET_FROM_JSON(id);
		SET_FROM_JSON(name);
		SET_FROM_JSON(icon);
		if ((it->type == MI_GENERATOR) && (it->generator != NULL)) {
			// Backwards compatiblity thing: If 'rows' key is defined,
			// use it as parameter.
			double rows = json_object_get_double(item, "rows", NULL);
			if (rows > 0.0) {
				char* new_generator = strbuilder_fmt("%s(%g)", it->generator, rows);
				if (new_generator != NULL) {
					// OOM here is not really that important.
					free((char*)it->generator);
					it->generator = new_generator;
				}
			}
		}
		#undef SET_FROM_JSON
		
		const char* actionstr = json_object_get_string(item, "action");
		if (actionstr != NULL) {
			ActionOE aoe = scc_parse_action(actionstr);
			if (IS_ACTION_ERROR(aoe)) {
				WARN("Failed to decode: '%s': %s", actionstr, ACTION_ERROR(aoe)->message);
				RC_REL(ACTION_ERROR(aoe));
			} else {
				it->action = ACTION(aoe);
			}
		}
		
		while (it->id == NULL) {
			// Autogenerate item id
			if (it->type == MI_ACTION)
				*(MenuItemType*)&it->type = MI_DUMMY;
			it->id = strbuilder_fmt("auto-id-%lx", next_auto_id++);
			if (it->id == NULL) goto scc_menudata_from_json_oom;
			if (scc_menudata_get_by_id(&dt->menudata, it->id) != NULL) {
				// ID already used
				free((char*)it->id);
				it->id = NULL;
			}
		}
		
		if (!list_add(dt->items, it))
			goto scc_menudata_from_json_oom;
		it = NULL;
	}
	
	json_free_context(ctx);
	return &dt->menudata;

scc_menudata_from_json_oom:
	LERROR("Failed to decode '%s': out of memory", filename);
	if (it != NULL) menuitem_free(it);
scc_menudata_from_json_invalid:
	json_free_context(ctx);
	if (dt != NULL) scc_menudata_free(&dt->menudata);
	return NULL;
}

static bool contains_generators(struct _MenuData* dt) {
	FOREACH_IN(MenuItem*, i, dt->items) {
		if ((i->type == MI_GENERATOR) && (i->generator != NULL))
			return true;
	}
	return false;
}

int scc_menudata_apply_generators(MenuData* _dt, Config* cfg) {
	struct _MenuData* dt = container_of(_dt, struct _MenuData, menudata);
	int rv = 1;				// 1 - all OK
	int failsafe = 10;		// Failsafe is here only to prevent generator generating generators and bombing entire process
	int next_auto_id = 0;
	for (; (failsafe > 0) && contains_generators(dt); failsafe--) {
		for (size_t index = 0; index<list_len(dt->items); index++) {
			MenuItem* i = list_get(dt->items, index);
			if ((i->type == MI_GENERATOR) && (i->generator != NULL)) {
				int error;
				list_remove(dt->items, i);
				MenuData* generated = scc_menudata_from_generator(i->generator, cfg, &error);
				if (generated == NULL) {
					if (error == 4) {
						menuitem_free(i);
						return 4;			// 4 - OOM
					} else if (error != 0) {
						WARN("Generator '%s' failed", i->generator);
						rv = 0;				// 0 - failed to generate
					}
				} else {
					struct _MenuData* generated_ = container_of(generated, struct _MenuData, menudata);
					MItemList generated_lst = generated_->items;
					for (size_t j=0; j<list_len(generated_lst); j++) {
						MenuItem* gi = list_get(generated_lst, j);
						// If item has no ID (usually), new will be assigned here
						while (gi->id == NULL) {
							gi->id = strbuilder_fmt("menugen-id-%lx", next_auto_id++);
							if (gi->id == NULL) {
								menuitem_free(i);
								scc_menudata_free(generated);
								return 4;		// 4 - OOM
							}
							if (scc_menudata_get_by_id(_dt, gi->id) != NULL) {
								// ID already used
								free((char*)gi->id);
								gi->id = NULL;
							}
						}
						if (!list_insert(dt->items, index, gi)) {
							menuitem_free(i);
							scc_menudata_free(generated);
							return 4;			// 4 - OOM
						}
						// Item is moved, not just copied. That way, it will not be
						// deallocated once scc_menudata_free is called.
						list_set(generated_lst, j, NULL);
						index ++;
					}
					scc_menudata_free(generated);
				}
				menuitem_free(i);
			}
		}
	}
	return rv;
}


#if MENU_GENERATORS_ENABLED

struct _GeneratorContext {
	GeneratorContext ctx;
	struct _MenuData* data;
	ParameterList params;
	Config* config;
	bool failed;
};

static bool ctx_add_action(GeneratorContext* _ctx, const char* name, const char* icon, Action* action) {
	struct _GeneratorContext* ctx = container_of(_ctx, struct _GeneratorContext, ctx);
	if (ctx->failed) return false;
	MenuItem* item = menuitem_new(MI_ACTION);
	if (item == NULL)
		goto scc_menu_generator_add_item_oom;
	if (name != NULL) {
		*((char**)&item->name) = strbuilder_cpy(name);
		if (item->name == NULL)
			goto scc_menu_generator_add_item_oom;
	}
	if (icon != NULL) {
		*((char**)&item->icon) = strbuilder_cpy(icon);
		if (item->icon == NULL)
			goto scc_menu_generator_add_item_oom;
	}
	*((Action**)&item->action) = (action != NULL) ? action : NoAction;
	if (!list_add(ctx->data->items, item))
		goto scc_menu_generator_add_item_oom;
	return true;
	
scc_menu_generator_add_item_oom:
	ctx->failed = true;
	RC_REL(item->action);
	free((char*)item->name);
	free((char*)item->icon);
	free(item);
	return false;
}

static Config* ctx_get_config(GeneratorContext* _ctx) {
	struct _GeneratorContext* ctx = container_of(_ctx, struct _GeneratorContext, ctx);
	return ctx->config;
}

static Parameter* ctx_get_parameter(GeneratorContext* _ctx, size_t index) {
	struct _GeneratorContext* ctx = container_of(_ctx, struct _GeneratorContext, ctx);
	if (ctx->params == NULL)
		return NULL;
	if (index >= list_len(ctx->params))
		return NULL;
	return list_get(ctx->params, index);
}


MenuData* scc_menudata_from_generator(const char* generator, Config* config, int* error) {
	// TODO: Check freeing memory here
	struct _MenuData* rv = NULL;
	char* filename = NULL;
	char error_str[256];
	*error = 4;		// OOM
	
	// Prepare library name & load library
	filename = strbuilder_cpy(generator);
	if (filename == NULL)
		return NULL;	// OOM
	if (strchr(generator, '('))
		*(filename + (strchr(generator, '(') - generator)) = 0;
	
	extlib_t lib = scc_load_library(SCLT_GENERATOR, "libscc-menugen-", filename, error_str);
	if (lib == NULL) {
		LERROR("Failed to load '%s': %s", filename, error_str);
		*error = 1;		// not found
		goto scc_menudata_from_generator_cleanup;
	}
	scc_menu_generator_generate_fn generate_fn = (scc_menu_generator_generate_fn)scc_load_function(lib, "generate", error_str);
	if (generate_fn == NULL) {
		LERROR("Failed to load 'scc_menu_generator_get_items' function from '%s': Windows error 0x%x", filename, error_str);
		*error = 2;		// found, but failed
		goto scc_menudata_from_generator_cleanup;
	}
	
	// Prepare context
	struct _GeneratorContext ctx = {
		.ctx = {
			ctx_add_action,
			ctx_get_config,
			ctx_get_parameter
		},
		.data = malloc(sizeof(struct _MenuData)),
		.params = NULL,
		.config = config,
		.failed = false
	};
	
	if (ctx.data == NULL) goto scc_menudata_from_generator_cleanup;
	ctx.data->items = list_new(MenuItem, 0);
	if (ctx.data->items == NULL) goto scc_menudata_from_generator_cleanup;
	
	// Parse parameters
	char* param_str = strchr(generator, '(');
	if (param_str != NULL) {
		ParamError* err;
		Tokens* tokens = tokenize(param_str);
		if (tokens == NULL)
			goto scc_menudata_from_generator_cleanup;
		ctx.params = _scc_tokens_to_param_list(tokens, &err);
		tokens_free(tokens);
		if (err != NULL) {
			LERROR("Failed to parse generator arguments: %s", err->message);
			RC_REL(err);
			*error = 3;
			goto scc_menudata_from_generator_cleanup;
		}
	}
	
	// Generate
	generate_fn(&ctx.ctx);
	
	// Check results
	if (ctx.failed) {
		// OOM durring generation
		scc_menudata_free(&ctx.data->menudata);
		goto scc_menudata_from_generator_cleanup;
	}
	if (list_len(ctx.data->items) == 0) {
		// Generator finished, but generated no data
		*error = 0;
		goto scc_menudata_from_generator_cleanup;
	}
	
	*error = 0;
	ctx.data->menudata.iter_get = &menudata_iter_get;
	rv = ctx.data;
	
scc_menudata_from_generator_cleanup:
	scc_close_library(lib);
	free(filename);
	if (ctx.params != NULL)
		list_free(ctx.params);
	if ((rv == NULL) && (ctx.data != NULL))
		scc_menudata_free(&ctx.data->menudata);
	return &rv->menudata;
}

#else

MenuData* scc_menudata_from_generator(const char* generator, Config* config, int* error) {
	*error = 0;
	return NULL;
}

#endif

