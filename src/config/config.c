/**
 * SC Controller - config
 * 
 * Handles loading, storing and querying config file
 */
#define LOG_TAG "config"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/hashmap.h"
#include "scc/utils/aojls.h"
#include "scc/config.h"
#include "scc/tools.h"
#include <stdlib.h>
#include <unistd.h>

/** No path (requested or used ) should be longer than this */
#define JSONPATH_MAX_LEN		256

typedef enum ConfigValueType {
	CVT_STRING,
	CVT_DOUBLE,
	CVT_BOOL,
	CVT_INT,
} ConfigValueType;


struct config_item {
	const char*				json_path;
	const ConfigValueType	type;
	union {
		const bool			v_bool;
		const char*			v_str;
		const int64_t		v_int;
		const double		v_double;
	};
	json_value_t*			value;
};

/**
 * Default list of recent profiles.
 *
 * Related value in config file is updated by scc-osd-daemon,
 * as that's only thing actually knowing what to put here.
 */
const char* DEFAULT_PROFILES[] = {
	"Desktop",
	"XBox Controller",
	"XBox Controller with High Precision Camera",
	NULL,
};

/**
 * Default list of enabled drivers. If driver is not listed in "drivers"
 * object, it's enabled only if listed here.
 */
const char* DEFAULT_ENABLED_DRIVERS[] = { "sc_by_cable" };


static struct config_item DEFAULT_VALUES[] = {
	
	/** Important stuff */
	
	/// true to show OSD message when profile is autoswitched
	{ "autoswitch_osd",						CVT_BOOL,		.v_bool = true },
	/// if enabled, another program with write access to  ~/.config/scc
	/// can ask daemon to send notifications about all (or only some) inputs.
	/// This enables GUI to display which physical button was pressed to user.
	{ "enable_sniffing",					CVT_BOOL,		.v_bool = false },
	// TODO: autoswitch: [] 	# Empty list of conditions
	/// number of profiles to keep
	{ "recent_max",							CVT_INT,		.v_int = 10 },
	/// List displayed in OSD
	// { "recent_profiles",					CVT_STRING_LST,	.ptr = (void*)default_profiles },
	/// If driver is listed here, it will not be loaded
	// { "disabled_drivers",					CVT_STRING_LST,	.ptr = (void*)default_disabled_drivers },
	/// If enabled, attempt is done to deatach emulated controller
	/// from 'Virtual core pointer' core device
	{ "fix_xinput",							CVT_BOOL,		.v_bool = true },
	/// If enabled, serial numbers are not readed from physical controller.
	/// This is workaround for some controllers stopping communicating when
	/// such request is recieved.
	{ "ignore_serials",						CVT_BOOL,		.v_bool = false },
	
	/** OSD style and colors config */
	{ "osd_style",							CVT_STRING,		.v_str = "Classic.gtkstyle.css" },
	{ "osd_colors/background",				CVT_STRING, 	.v_str = "101010" },
	{ "osd_colors/border",					CVT_STRING, 	.v_str = "00FF00" },
	{ "osd_colors/text",					CVT_STRING, 	.v_str = "16BF24" },
	{ "osd_colors/menuitem_border",			CVT_STRING, 	.v_str = "001500" },
	{ "osd_colors/menuitem_hilight",		CVT_STRING, 	.v_str = "000070" },
	{ "osd_colors/menuitem_hilight_text",	CVT_STRING, 	.v_str = "16FF26" },
	{ "osd_colors/menuitem_hilight_border",	CVT_STRING, 	.v_str = "00FF00" },
	{ "osd_colors/menuseparator",			CVT_STRING, 	.v_str = "109010" },
	
	/** Colors used by on-screen keyboard */
	{ "osk_colors/hilight",					CVT_STRING,		.v_str = "00688D" },
	{ "osk_colors/pressed",					CVT_STRING,		.v_str = "1A9485" },
	{ "osk_colors/button1",					CVT_STRING,		.v_str = "162082" },
	{ "osk_colors/button1_border",			CVT_STRING,		.v_str = "262b5e" },
	{ "osk_colors/button2",					CVT_STRING,		.v_str = "162d44" },
	{ "osk_colors/button2_border",			CVT_STRING,		.v_str = "27323e" },
	{ "osk_colors/text",					CVT_STRING,		.v_str = "ffffff" },
	
	/** Colors used by gesture display. Unlike OSD and OSK, these are RGBA */
	{ "gesture_colors/background",			CVT_STRING,		.v_str = "160c00ff" },
	{ "gesture_colors/grid",				CVT_STRING,		.v_str = "004000ff" },
	{ "gesture_colors/line",				CVT_STRING,		.v_str = "ffffff1a" },
	
	// Opacity of OSD windows
	{ "windows_opacity",					CVT_DOUBLE,		.v_double = 0.95 },
	
	/** GUI config */
	
	/// If enabled, GUI will display status icon
	{ "gui/enable_status_icon",				CVT_BOOL,		.v_bool = false },
	/// If enabled, GUI will hide to status icon instead of minimizing
	{ "gui/minimize_to_status_icon",		CVT_BOOL,		.v_bool = false },
	/// If enabled, GUI will start minimized
	{ "gui/minimize_on_start",				CVT_BOOL,		.v_bool = false },
	/// If enabled, scc-deamon will be terminated when GUI is closed
	{ "gui/autokill_daemon",				CVT_BOOL,		.v_bool = false },
	/// If enabled, GUI will display "new in this version" message
	{ "gui/news/enabled",					CVT_BOOL,		.v_bool = false },
	/// Stores last version when "new in this version" was shown
	{ "gui/news/last_version",				CVT_STRING,		.v_str = "0.3.12" },
	
	// TODO: "controllers": { },
	// TODO: Output - modifies emulated controller
	/*
	 * # Changing this may be usefull, but can break a lot of things
	 * "output": {
	 * 	'vendor'	: '0x045e',
	 * 	'product'	: '0x028e',
	 * 	'version'	: '0x110',
	 * 	'name'		: "Microsoft X-Box 360 pad",
	 * 	'buttons'	: 11,
	 * 	'rumble'	: True,
	 * 	'axes'	: [
	 * 		(-32768, 32767),	# Axes.ABS_X
	 * 		(-32768, 32767),	# Axes.ABS_Y
	 * 		(-32768, 32767),	# Axes.ABS_RX
	 * 		(-32768, 32767),	# Axes.ABS_RY
	 * 		(0, 255),			# Axes.ABS_Z
	 * 		(0, 255),			# Axes.ABS_RZ
	 * 		(-1, 1),			# Axes.ABS_HAT0X
	 * 		(-1, 1)				# Axes.ABS_HAT0Y
	 * 	],
	 * },
	 */
	
	{ NULL },
};


struct _Config {
	// Private version of Config
	Config			config;
	char			buffer[JSONPATH_MAX_LEN];
	aojls_ctx_t*	ctx;
};


static void config_dealloc(void* _c) {
	struct _Config* c = container_of(_c, struct _Config, config);
	
	json_free_context(c->ctx);
	free(c);
}

static inline struct _Config* config_new() {
	struct _Config* c = malloc(sizeof(struct _Config));
	if (c == NULL) return NULL;
	RC_INIT(&c->config, &config_dealloc);
	c->ctx = NULL;
	return c;
}

static long json_reader_fn(char* buffer, size_t len, void* reader_data) {
	return read(*((int*)reader_data), buffer, len);
}

/** JSON-parsing part of config_load_from */
static bool config_load_json_file(struct _Config* c, int fd, char* error_return, size_t error_limit) {
	aojls_deserialization_prefs prefs = {
		.reader = &json_reader_fn,
		.reader_data = (void*)&fd
	};
	
	c->ctx = aojls_deserialize(NULL, 0, &prefs);
	if ((c->ctx == NULL) || (prefs.error != NULL)) {
		LERROR("Failed to decode configuration: %s", prefs.error);
		if (error_return != NULL) {
			strncpy(error_return, prefs.error, error_limit);
			error_return[error_limit - 1] = 0;
		}
		json_free_context(c->ctx);
		c->ctx = NULL;
		return false;
	}
	
	return true;
}

Config* config_load() {
	struct _Config* c = config_new();
	if (c == NULL) return NULL;
	
	// TODO: Load from file
	return &c->config;
}

Config* config_load_from(int fd, char* error_return, size_t error_limit) {
	if (error_return != NULL)
		error_return[0] = 0;
	
	struct _Config* c = config_new();
	if (c == NULL) return NULL;
	
	if (!config_load_json_file(c, fd, error_return, error_limit)) {
		// Failed to load
		config_dealloc(&c->config);
		return NULL;
	}
	return &c->config;
}


static inline struct config_item* config_get_default(struct _Config* c, const char* json_path) {
	for (struct config_item* v = DEFAULT_VALUES; v->json_path != NULL; v++)
		if (strcmp(v->json_path, json_path) == 0)
			return v;
	return NULL;	
}

static inline json_value_t* config_get_value(struct _Config* c, const char* json_path) {
	json_object* obj = json_as_object(json_context_get_result(c->ctx));
	while (obj != NULL) {
		const char* slash = strchr(json_path, '/');
		if (slash != NULL) {
			size_t slash_index = slash - json_path;
			if (slash_index >= JSONPATH_MAX_LEN)
				// Requested path is too long, this is not reasonable thing to request
				return NULL;
			strncpy(c->buffer, json_path, JSONPATH_MAX_LEN);
			c->buffer[slash_index] = 0;
			obj = json_object_get_object(obj, c->buffer);
			json_path = &json_path[slash_index + 1];
		} else {
			return json_object_get_object_as_value(obj, json_path);
		}
	}
	return NULL;
}

const char* config_get(Config* _c, const char* json_path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	json_value_t* value = config_get_value(c, json_path);
	if ((value != NULL) && (json_get_type(value) == JS_STRING))
		return json_as_string(value);
	
	struct config_item* def = config_get_default(c, json_path);
	if ((def != NULL) && (def->type == CVT_STRING))
		return def->v_str;
	
	return NULL;
}

int64_t config_get_int(Config* _c, const char* json_path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	json_value_t* value = config_get_value(c, json_path);
	if (value != NULL) {
		bool correct = true;
		double d_value = json_as_number(value, &correct);
		if (correct)
			return (int64_t)d_value;
	}
	
	struct config_item* def = config_get_default(c, json_path);
	if ((def != NULL) && (def->type == CVT_INT))
		return def->v_int;
	
	return 0;
}

double config_get_double(Config* _c, const char* json_path) {
	struct _Config* c = container_of(_c, struct _Config, config);
	json_value_t* value = config_get_value(c, json_path);
	if (value != NULL) {
		bool correct = true;
		double d_value = json_as_number(value, &correct);
		if (correct)
			return d_value;
	}
	
	struct config_item* def = config_get_default(c, json_path);
	if ((def != NULL) && (def->type == CVT_INT))
		return def->v_double;
	
	return 0;
}

size_t config_get_recents(Config* _c, const char** target, size_t limit) {
	struct _Config* c = container_of(_c, struct _Config, config);
	json_array* value = json_as_array(config_get_value(c, "recent_profiles"));
	size_t j = 0;
	if (value == NULL) {
		for (size_t i=0; (i<limit) && (DEFAULT_PROFILES[i]!=NULL); i++) {
			target[i] = DEFAULT_PROFILES[i];
			j++;
		}
	} else {
		for (size_t i=0; (i<limit) && (i<json_array_size(value)); i++) {
			const char* s = json_array_get_string(value, i);
			if (s != NULL) {
				target[j] = s;
				j++;
			}
		}
	}
	return j;
}
