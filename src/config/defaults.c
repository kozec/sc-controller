/**
 * SC Controller - default values.
 * 
 * This is common for both Windows and rest.
 */
#define LOG_TAG "config"
#include "scc/utils/logging.h"
#include "config.h"

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

const struct config_item DEFAULTS[] = {
	
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
	{ "recent_profiles",					CVT_STR_ARRAY,	.v_strar = DEFAULT_PROFILES },
	/// If driver is listed here, it will not be loaded
	// { "disabled_drivers",					CVT_STRING_LST,	.ptr = (void*)default_disabled_drivers },
#ifndef _WIN32
	/// If enabled, attempt is done to deatach emulated controller
	/// from 'Virtual core pointer' core device
	{ "fix_xinput",							CVT_BOOL,		.v_bool = true },
#endif
	/// If enabled, serial numbers are not readed from physical controller.
	/// This is workaround for some controllers stopping communicating when
	/// such request is recieved.
	{ "ignore_serials",						CVT_BOOL,		.v_bool = false },
	
	/** OSD style and colors config */
	{ "osd_style",							CVT_STRING,		.v_str = "Reloaded.gtkstyle.css" },
	{ "osd_color_theme",					CVT_STRING,		.v_str = "Green.colors.json" },
	{ "osd_colors/background",				CVT_STRING, 	.v_str = "#101010" },
	{ "osd_colors/border",					CVT_STRING, 	.v_str = "#00FF00" },
	{ "osd_colors/text",					CVT_STRING, 	.v_str = "#16BF24" },
	{ "osd_colors/menuitem_border",			CVT_STRING, 	.v_str = "#001500" },
	{ "osd_colors/menuitem_hilight",		CVT_STRING, 	.v_str = "#000070" },
	{ "osd_colors/menuitem_hilight_text",	CVT_STRING, 	.v_str = "#16FF26" },
	{ "osd_colors/menuitem_hilight_border",	CVT_STRING, 	.v_str = "#00FF00" },
	{ "osd_colors/menuseparator",			CVT_STRING, 	.v_str = "#109010" },
	
	/** Colors used by on-screen keyboard */
	{ "osk_colors/hilight",					CVT_STRING,		.v_str = "#00688D" },
	{ "osk_colors/pressed",					CVT_STRING,		.v_str = "#1A9485" },
	{ "osk_colors/button1",					CVT_STRING,		.v_str = "#162082" },
	{ "osk_colors/button1_border",			CVT_STRING,		.v_str = "#262b5e" },
	{ "osk_colors/button2",					CVT_STRING,		.v_str = "#162d44" },
	{ "osk_colors/button2_border",			CVT_STRING,		.v_str = "#27323e" },
	{ "osk_colors/text",					CVT_STRING,		.v_str = "#ffffff" },
	
	/** Colors used by gesture display. Unlike OSD and OSK, these are RGBA */
	{ "gesture_colors/background",			CVT_STRING,		.v_str = "#160c00ff" },
	{ "gesture_colors/grid",				CVT_STRING,		.v_str = "#004000ff" },
	{ "gesture_colors/line",				CVT_STRING,		.v_str = "#ffffff1a" },
	
	// Opacity of OSD windows
	{ "windows_opacity",					CVT_DOUBLE,		.v_double = 0.95 },
	
	/** GUI config */
	
	{ "gui",								CVT_OBJECT },
	/// If enabled, GUI will display status icon
	{ "gui/enable_status_icon",				CVT_BOOL,		.v_bool = false },
	/// If enabled, GUI will hide to status icon instead of minimizing
	{ "gui/minimize_to_status_icon",		CVT_BOOL,		.v_bool = false },
	/// If enabled, GUI will start minimized
	{ "gui/minimize_on_start",				CVT_BOOL,		.v_bool = false },
	/// If enabled, scc-deamon will be terminated when GUI is closed
	{ "gui/autokill_daemon",				CVT_BOOL,		.v_bool = false },
	/// If enabled, GUI will display "new in this version" message
	{ "gui/news/enabled",					CVT_BOOL,		.v_bool = true },
	/// Stores last version when "new in this version" was shown
	{ "gui/news/last_version",				CVT_STRING,		.v_str = "0.3.12" },
	/// Output - modifies emulated controller
	/// On windows, this is just string 'x360', 'ds4' or 'auto'
	{ "output",								CVT_STRING,		.v_str = "auto" },
	
	// TODO: Output on Linux
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

const struct config_item CONTROLLER_DEFAULTS[] = {
	{ "axes",					CVT_OBJECT },
	{ "dpads",					CVT_OBJECT },
	{ "buttons",				CVT_OBJECT },
	{ "emulate_c",				CVT_BOOL },
	
	{ "led_level",				CVT_INT,			.v_int =  80 },
	{ "menu_cancel",			CVT_STRING,			.v_str = "B" },
	{ "menu_confirm",			CVT_STRING,			.v_str = "A" },
	{ "menu_control", 			CVT_STRING,			.v_str = "STICK" },
	{ "idle_timeout",			CVT_INT,			.v_int = 600 },
	{ "osd_alignment",			CVT_INT,			.v_int = 0 },
	
	{ "input_rotation",			CVT_OBJECT },
	{ "input_rotation/left",	CVT_DOUBLE,			.v_double = 0.0 },
	{ "input_rotation/right",	CVT_DOUBLE,			.v_double = 0.0 },
	
	{ "gui",					CVT_OBJECT },
	{ "gui/icon",				CVT_STRING,			.v_str = "" },
	{ "gui/name",				CVT_STRING,			.v_str = "" },
	{ "gui/buttons",			CVT_STR_ARRAY,		.v_strar = NULL },
	{ NULL },
};


const struct config_item* config_get_default(struct _Config* c, const char* path) {
	for (const struct config_item* v = c->defaults; v->path != NULL; v++) {
		if (strcmp(v->path, path) == 0)
			return v;
	}
	return NULL;
}

bool config_fill_defaults(Config* _c) {
	struct _Config* c = container_of(_c, struct _Config, config);
	bool change = false;
	for (const struct config_item* v = c->defaults; v->path != NULL; v++) {
		const config_value_t* value = config_get_value(c, v->path, v->type);
		if (value == NULL) {
			switch (v->type) {
			case CVT_OBJECT:
			case CVT_INVALID:
				break;
			case CVT_STRING:
				if (1 != config_set(_c, v->path, v->v_str))
					return false;
				change = true;
				break;
			case CVT_STR_ARRAY:
				if (1 != config_set_strings(_c, v->path, v->v_strar, -1))
					return false;
				change = true;
				break;
			case CVT_INT:
				if (1 != config_set_int(_c, v->path, v->v_int))
					return false;
				change = true;
				break;
			case CVT_BOOL:
				if (1 != config_set_int(_c, v->path, v->v_bool ? 1 : 0))
					return false;
				change = true;
				break;
			case CVT_DOUBLE:
				if (1 != config_set_double(_c, v->path, v->v_double))
					return false;
				change = true;
				break;
			}
		}
	}
	return change;
}
