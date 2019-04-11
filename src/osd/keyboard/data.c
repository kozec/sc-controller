#define LOG_TAG "OSD"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/aojls.h"
#include "scc/config.h"
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include "keyboard.h"


static long json_reader_fn(char* buffer, size_t len, void* reader_data) {
	return read(*((int*)reader_data), buffer, len);
}

void load_colors(OSDKeyboardPrivate* priv) {
	Config* config = config_load();
	ASSERT(config);
	
	gdk_rgba_parse(&priv->color_pressed, config_get(config, "osk_colors/pressed"));
	gdk_rgba_parse(&priv->color_hilight, config_get(config, "osk_colors/hilight"));
	gdk_rgba_parse(&priv->color_button2, config_get(config, "osk_colors/button2"));
	gdk_rgba_parse(&priv->color_button1, config_get(config, "osk_colors/button1"));
	gdk_rgba_parse(&priv->color_button1_border, config_get(config, "osk_colors/button1_border"));
	gdk_rgba_parse(&priv->color_text, config_get(config, "osk_colors/text"));
	
	RC_REL(config);
}

static inline bool load_limit(struct Limits* limit, json_array* arr) {
	if (arr == NULL) {
		LERROR("Failed to load limits: item not found");
		return false;
	}
	if (json_array_size(arr) != 4) {
		LERROR("Failed to load limits: Wrong array size");
		return false;
	}
	limit->x0 = json_array_get_double(arr, 0, NULL);
	limit->y0 = json_array_get_double(arr, 1, NULL);
	limit->x1 = json_array_get_double(arr, 2, NULL);
	limit->y1 = json_array_get_double(arr, 3, NULL);
	return true;
}

bool load_keyboard_data(const char* filename, OSDKeyboardPrivate* priv) {
	int fp = open(filename, O_RDONLY);
	if (fp < 0) {
		LERROR("Failed to open '%s': %s", filename, strerror(errno));
		return false;
	}
	aojls_deserialization_prefs prefs = {
		.reader = &json_reader_fn,
		.reader_data = (void*)&fp
	};
	aojls_ctx_t* json_ctx = aojls_deserialize(NULL, 0, &prefs);
	close(fp);
	if ((json_ctx == NULL) || (prefs.error != NULL)) {
		LERROR("Failed to decode '%s': %s", filename, prefs.error);
		json_free_context(json_ctx);
		return false;
	}
	
	json_object* root = (json_object*)json_context_get_result(json_ctx);
	json_array* buts = json_object_get_array(root, "buttons");
	if ((buts == NULL) || (json_array_size(buts) < 1)) {
		LERROR("Found no buttons in '%s'", filename);
		json_free_context(json_ctx);
		return false;
	}
	
	if (!list_allocate(priv->buttons, json_array_size(buts)))
		goto load_keyboard_data_oom;
	
	
	json_array* size = json_object_get_array(root, "size");
	vec_set(priv->size,
		json_array_get_double(size, 0, NULL),
		json_array_get_double(size, 1, NULL)
	);
	
	json_object* json_limits;
	// json_array* json_limit;
	if ((json_limits = json_object_get_object(root, "limits")) == NULL)
		return false;
	if (!load_limit(&priv->limits[0], json_object_get_array(json_limits, "left")))
		return false;
	if (!load_limit(&priv->limits[1], json_object_get_array(json_limits, "right")))
		return false;
	if (!load_limit(&priv->limits[2], json_object_get_array(json_limits, "cpad")))
		return false;
	
	for (size_t i=0; i<json_array_size(buts); i++) {
		json_object* json_b = json_array_get_object(buts, i);
		json_array* pos  = json_object_get_array(json_b, "pos");
		json_array* size = json_object_get_array(json_b, "size");
		const char* action_str = json_object_get_string(json_b, "action");
		// If 'json_b' is NULL, everything else will be NULL
		if ((action_str == NULL)
			|| (pos == NULL) || (json_array_size(pos) != 2)
			|| (size == NULL) || (json_array_size(size) != 2)
		) {
			WARN("Failed to decode button at index %i from '%s'", i, filename);
			continue;
		}
		Button* b = malloc(sizeof(Button));
		if (b == NULL) goto load_keyboard_data_oom;
		
		ActionOE aoe = scc_parse_action(action_str);
		if (IS_ACTION_ERROR(aoe)) {
			WARN("Failed to decode button at index %i from '%s': %s",
						i, filename, ACTION_ERROR(aoe)->message);
			RC_REL(ACTION_ERROR(aoe));
			free(b);
			continue;
		}
		b->pressed = b->hilighted = false;
		b->action = ACTION(aoe);
		b->keycode = 0;
		b->dark = json_object_get_bool_default(json_b, "dark", false);
		if (b->action->flags & AF_KEYCODE) {
			Parameter* p = b->action->get_property(b->action, "keycode");
			if (p != NULL) b->keycode = scc_parameter_as_int(p);
			RC_REL(p);
		}
		b->label = (b->keycode != 0) ? NULL : scc_action_get_description(b->action, AC_OSK);
		vec_set(b->pos, json_array_get_double(pos, 0, NULL),
							json_array_get_double(pos, 1, NULL));
		vec_set(b->size, json_array_get_double(size, 0, NULL),
							json_array_get_double(size, 1, NULL));
		list_add(priv->buttons, b);
	}
	
	json_free_context(json_ctx);
	return true;
	
load_keyboard_data_oom:
	LERROR("Out of memory while decoding buttons");
	json_free_context(json_ctx);
	return false;
}


