#define LOG_TAG "menu_data.c"
#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/aojls.h"
#include "scc/utils/list.h"
#include "scc/utils/rc.h"
#include "scc/menu_data.h"
#include "scc/action.h"
#include "scc/parser.h"
#include <errno.h>
#include <stdlib.h>

typedef LIST_TYPE(MenuItem) ItemsList;

struct _MenuData {
	MenuData			menudata;
	ItemsList			items;
};

long json_reader_fn(char* buffer, size_t len, void* reader_data);

static MenuItem* menuitem_new(MenuItemType t) {
	MenuItem* i = malloc(sizeof(MenuItem));
	memset(i, 0, sizeof(MenuItem));
	*(MenuItemType*)&i->type = t;
	*(size_t*)&i->rows = 5;
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
		if (strcmp(i->id, id) == 0) {
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
		double rows = json_object_get_double(item, "rows", NULL);
		if (rows < 1.0) rows = 5.0;
		*(size_t*)&it->rows = (size_t)rows;
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
