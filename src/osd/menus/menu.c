#define LOG_TAG "OSD"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/argparse.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/osd/osd_window.h"
#include "scc/osd/osd_menu.h"
#include "scc/virtual_device.h"
#include "scc/special_action.h"
#include "scc/controller.h"
#include "scc/menu_data.h"
#include "scc/config.h"
#include <glib.h> // glib.h has to be included before client.h
#include "scc/client.h"
#include "scc/tools.h"
#include "../osd.h"
#include <gtk/gtk.h>
#include <string.h>

/**
 * How GUI options maps to menu behaviour:
 *
 *          confirm   cancel
 * Con Can ByCl ByRel ByRel
 * def def  0     0     0		menu('x.menu')					 // [1]
 * A   def  0     0     0		menu('x.menu',DEFAULT,A)		 // cancels by release
 * A   X    0     0     0		menu('x.menu',DEFAULT,A,X)
 * -   X    1     0     0		menu('x.menu',DEFAULT,DEFAULT,X) // confirms by press
 * -   def  0     0     0		menu('x.menu')					 // [1]
 * -   def  0     1     0		menu('x.menu',DEFAULT,SAME)		 // broken
 * -   -    1     0     1		menu('x.menu')					 // [1]
 *
 * [1] this is default behaviour on pads
 */

#define SUBMENU_OFFSET	20

typedef struct _OSDMenuPrivate		OSDMenuPrivate;

struct _OSDMenu {
	GtkWindow						parent;
	OSDMenuPrivate*					priv;
};

struct _OSDMenuClass {
	GtkWindowClass					parent_class;
};

struct _OSDMenuPrivate {
	StickController*				sc;
	MenuData*						data;
	void*							plugin_data;
	SCCClient*						client;
	GtkWidget*						selected;
	GtkWidget*						cursor;
	GtkWidget*						fixed;
	OSDMenu*						child;
	extlib_t						plugin;
	Mapper*							slave_mapper;
	osd_menu_handle_stick_fn		handle_stick_cb;
	osd_menu_handle_input_fn		handle_input_cb;
	OSDMenuSettings					settings;
};

G_DEFINE_TYPE_WITH_CODE(OSDMenu, osd_menu, OSD_WINDOW_TYPE, G_ADD_PRIVATE(OSDMenu));


static void osd_menu_exit(OSDMenu* mnu, int code);
static void osd_menu_finalize(GObject* mnu);

static void osd_menu_class_init(OSDMenuClass *klass) {
	GObjectClass* c = G_OBJECT_CLASS(klass);
	c->finalize = osd_menu_finalize;
}


static inline bool point_in_gtkrect(GtkWidget* w, double x, double y) {
	GtkAllocation al;
	gtk_widget_get_allocation(w, &al);
	return ((x >= al.x) && (y >= al.y)
				&& (x <= al.x + al.width)
				&& (y <= al.y + al.height));
}


/** Returns -1 if widget is not found */
static int get_menuitem_index(MenuData* dt, GtkWidget* widget) {
	if (widget == NULL)
		return -1;
	for (int x=0; x<scc_menudata_len(dt); x++) {
		MenuItem* i = scc_menudata_get_by_index(dt, x);
		if (i->userdata == widget)
			return x;
	}
	return -1;
}


inline static OSDMenuPrivate* get_private(OSDMenu* mnu) {
	return G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
}


static void on_mnu_child_exit(void* _child, int code, void* _mnu) {
	OSDMenu* mnu = (OSDMenu*)_mnu;
	OSDMenuPrivate* priv = get_private(mnu);
	if (code == -1) {
		// Canceled
		gtk_widget_destroy(GTK_WIDGET(priv->child));
		priv->child = NULL;
		gtk_widget_set_name(GTK_WIDGET(mnu), "osd-menu");
	} else {
		osd_window_exit(OSD_WINDOW(mnu), code);
	}
}


static void on_mnu_child_ready(void* _child, void* _mnu) {
	gtk_widget_show_all(GTK_WIDGET(_child));
	gtk_widget_set_name(GTK_WIDGET(_mnu), "osd-menu-inactive");
}


static gboolean osd_menu_on_data_ready(GIOChannel* source, GIOCondition condition, gpointer _mnu) {
	OSDMenu* mnu = OSD_MENU(_mnu);
	OSDMenuPrivate* priv = get_private(mnu);
	const char* message = sccc_recieve(priv->client);
	if (message != NULL) {
		if (message[0] == 0) {
			osd_menu_exit(mnu, 1);
			return false;
		}
	}
	return true;
}


static void osd_menu_connection_ready(SCCClient* c) {
	osd_menu_lock_inputs(OSD_MENU(c->userdata));
}

void osd_menu_lock_inputs(OSDMenu* mnu) {
	OSDMenuPrivate* priv = get_private(mnu);
	uint32_t handle = sccc_get_controller_handle(priv->client, priv->settings.controller_id);
	if (handle == 0) {
		if (priv->settings.controller_id == NULL)
			LERROR("There is no controller connected");
		else
			LERROR("Requested controller '%s' not connected", priv->settings.controller_id);
		osd_menu_exit(mnu, 4);
		return;
	}
	
	const char* control_with = scc_what_to_string(priv->settings.control_with);
	const char* confirm_with = scc_button_to_string(priv->settings.confirm_with);
	const char* cancel_with = scc_button_to_string(priv->settings.cancel_with);
	if (priv->settings.confirm_with == SCC_ALWAYS)
		confirm_with = control_with;
	if (!sccc_lock(priv->client, handle, control_with, confirm_with, cancel_with)) {
		LERROR("Failed to lock controller");
		osd_menu_exit(mnu, 3);
		return;
	}
	
	g_signal_emit_by_name(G_OBJECT(mnu), "ready");
}


void osd_menu_parse_event(OSDMenu* mnu, SCCClient* c, uint32_t handle,
					SCButton button, PadStickTrigger pst, int values[]) {
	OSDMenuPrivate* priv = get_private(mnu);
	if (priv->child != NULL)
		return osd_menu_parse_event(priv->child, c, handle, button, pst, values);
	if (priv->handle_input_cb != NULL) {
		OSDMenuInput translated_input = OMI_NOT_TRANSLATED;
		if (pst == priv->settings.control_with)
			translated_input = OMI_CONTROL;
		else if (button == priv->settings.cancel_with)
			translated_input = OMI_CANCEL;
		else if (button == priv->settings.confirm_with)
			translated_input = OMI_CONFIRM;
		return priv->handle_input_cb(mnu, button, pst, translated_input, values);
	}
	
	if ((pst == priv->settings.control_with) && priv->settings.use_cursor) {
		GtkAllocation al_cursor;
		GtkAllocation al_self;
		gtk_widget_get_allocation(priv->cursor, &al_cursor);
		gtk_widget_get_allocation(GTK_WIDGET(mnu), &al_self);
		if ((values[0] == 0) && (values[1] == 0))
			return;
		double x = (double)values[0] / (STICK_PAD_MAX * 2.0);
		double y = (double)values[1] / (STICK_PAD_MAX * 2.0);
		double pad_w = al_cursor.width * 0.5;
		double pad_h = al_cursor.height * 0.5;
		double max_w = al_self.width - (2.0 * pad_w);
		double max_h = al_self.height - (2.0 * pad_h);
		circle_to_square(&x, &y);
		x = clamp(pad_w, (pad_w + max_w) * 0.5 + x * max_w, max_w - pad_w);
		y = clamp(pad_h, (pad_h + max_h) * 0.5 + y * max_h * -1.0, max_h - pad_h);
		gtk_fixed_move(GTK_FIXED(priv->fixed), priv->cursor, x, y);
		
		ListIterator it = iter_get(priv->data);
		FOREACH(MenuItem*, i, it) {
			if (i->userdata == NULL) continue;
			if (point_in_gtkrect(GTK_WIDGET(i->userdata), x, y)) {
				osd_menu_select_index(mnu, get_menuitem_index(priv->data,
										GTK_WIDGET(i->userdata)));
			}
		}
		iter_free(it);
	} else if ((pst == priv->settings.control_with) && (priv->sc != NULL))
		stick_controller_feed(priv->sc, values);
	else if ((button == priv->settings.confirm_with) && (!values[0]))
		osd_menu_confirm(mnu);
	else if ((button == priv->settings.cancel_with) && (!values[0]))
		osd_menu_exit(mnu, -1);
}


static void osd_menu_on_event(SCCClient* c, uint32_t handle, SCButton button,
			PadStickTrigger pst, int values[]) {
	OSDMenu* mnu = OSD_MENU(c->userdata);
	osd_menu_parse_event(mnu, c, handle, button, pst, values);
}


static void osd_menu_on_reconfigured(SCCClient* c) {
	install_css_provider();
	LOG("Reconfigured.");
}

static void _osd_menu_handle_stick(int dx, int dy, void* _mnu) {
	OSDMenu* mnu = OSD_MENU(_mnu);
	OSDMenuPrivate* priv = get_private(mnu);
	priv->handle_stick_cb(mnu, dx, dy);
}

/**
 * Activates (calls 'pressed' handler) or deactivates (calls 'released hanlder')
 * specific menu item.
 * Doesn't works with submenus & etc.
 */
static void osd_menu_set_action_active(OSDMenu* mnu, MenuItem* i, bool active) {
	if (i == NULL) return;
	OSDMenuPrivate* priv = get_private(mnu);
	Action* a = NULL;
	
	switch (i->type) {
		case MI_ACTION:
			a = i->action;
			scc_action_compress(&a);
			if (active)
				a->button_press(a, priv->slave_mapper);
			else
				a->button_release(a, priv->slave_mapper);
			break;
		default:
			break;
	}
}

static void osd_menu_exit(OSDMenu* mnu, int code) {
	OSDMenuPrivate* priv = get_private(mnu);
	if ((priv->settings.confirm_with == SCC_ALWAYS) && (priv->selected != NULL)) {
		MenuItem* i = g_object_get_data(G_OBJECT(priv->selected), "scc-menu-item-data");
		osd_menu_set_action_active(mnu, i, false);
	}
	osd_window_exit(OSD_WINDOW(mnu), 2);
}


bool osd_menu_select_index(OSDMenu* mnu, size_t index) {
	OSDMenuPrivate* priv = get_private(mnu);
	return osd_menu_select(mnu, scc_menudata_get_by_index(priv->data, index));
}

bool osd_menu_select(OSDMenu* mnu, MenuItem* i) {
	OSDMenuPrivate* priv = get_private(mnu);
	bool always_action_kept = false;
	// if (first && (i->type == MI_ACTION)) {
	// 	gtk_widget_set_name(GTK_WIDGET(i->userdata), "osd-menu-item-selected");
	// 	first = false;
	// }
	// GtkWidget* old_selected = priv->selected;
	if (priv->selected != NULL) {
		char* name = strbuilder_cpy(gtk_widget_get_name(GTK_WIDGET(priv->selected)));
		ASSERT(name != NULL);
		char* suffix = strstr(name, "-selected");
		if (suffix != NULL) {
			suffix[0] = 0;
			gtk_widget_set_name(GTK_WIDGET(priv->selected), name);
		}
		free(name);
		if (priv->settings.confirm_with == SCC_ALWAYS) {
			if (priv->selected == i->userdata) {
				always_action_kept = true;
			} else {
				MenuItem* s = g_object_get_data(G_OBJECT(priv->selected), "scc-menu-item-data");
				osd_menu_set_action_active(mnu, s, false);
			}
		}
		priv->selected = NULL;
	}
	
	if ((i == NULL) || (i->id == NULL) || ((i->type != MI_ACTION) && (i->type != MI_SUBMENU)))
		// Not selectable
		return false;
	
	// TODO: This. Also note that priv->selected is c
	// if old_selected != i
	// 	if self.feedback and self.controller:
	// 		self.controller.feedback(*self.feedback)
	
	if ((priv->settings.confirm_with == SCC_ALWAYS) && !always_action_kept) {
		MenuItem* s = g_object_get_data(G_OBJECT(i->userdata), "scc-menu-item-data");
		osd_menu_set_action_active(mnu, s, true);
	}
	priv->selected = i->userdata;
	if (i->userdata != NULL) {
		StrBuilder* sb = strbuilder_new();
		ASSERT(sb != NULL);
		char* name = gtk_widget_get_name(GTK_WIDGET(priv->selected));
		if (name != NULL) {
			strbuilder_add(sb, name);
			strbuilder_add(sb, "-selected");
			ASSERT(!strbuilder_failed(sb));
			gtk_widget_set_name(GTK_WIDGET(priv->selected), strbuilder_get_value(sb));
		}
		strbuilder_free(sb);
		// GLib.timeout_add(2, self._check_on_screen_position)
	}
	return true;
}


void osd_menu_next_item(OSDMenu* mnu, int direction) {
	OSDMenuPrivate* priv = get_private(mnu);
	int start = get_menuitem_index(priv->data, priv->selected);
	int i = start + direction;
	while (1) {
		if (i == start) {
			// Cannot find valid menu item
			osd_menu_select_index(mnu, start);
			break;
		}
		if (i >= (int)scc_menudata_len(priv->data)) {
			i = 0;
			// TODO: GLib.timeout_add(1, self._check_on_screen_position, True)
			continue;
		}
		if (i < 0) {
			i = scc_menudata_len(priv->data) - 1;
			// TODO: GLib.timeout_add(1, self._check_on_screen_position, True)
			continue;
		}
		if (osd_menu_select_index(mnu, i)) {
			// Found valid item
			break;
		}
		i += direction;
		if (start < 0)
			start = 0;
	}
}


static bool osd_menu_sa_handler(Mapper* m, unsigned int sa_action_type, void* sa_data) {
	if (sa_action_type == SAT_KEYBOARD) {
		char* scc_osd_keyboard = scc_find_binary("scc-osd-keyboard");
		if (scc_osd_keyboard == NULL) {
			LERROR("Could not find 'scc-osd-keyboard'");
		} else {
			// On Windows, scc-osd-keyboard.exe may start before menu sucessfully exits,
			// what causes keyboard to fail to acquire locks. To prevent that, lock
			// is released before keyboard is displayed.
			OSDMenu* mnu = OSD_MENU(sccc_slave_mapper_get_userdata(m));
			OSDMenuPrivate* priv = get_private(mnu);
			sccc_unlock_all(priv->client);
			char* const argv[] = { scc_osd_keyboard, NULL };
			scc_spawn(argv, 0);
		}
		return true;
	}
	return false;
}


inline static Mapper* create_slave_mapper(SCCClient* client, OSDMenu* mnu) {
	Mapper* mapper = sccc_slave_mapper_new(client);
	if (mapper == NULL)
		return NULL;
	sccc_slave_mapper_set_userdata(mapper, mnu);
	sccc_slave_mapper_set_sa_handler(mapper, osd_menu_sa_handler);
	sccc_slave_mapper_set_devices(mapper,
		scc_virtual_device_create(VTP_KEYBOARD, NULL),
		scc_virtual_device_create(VTP_MOUSE, NULL));
	return mapper;
}

bool osd_menu_set_client(OSDMenu* mnu, SCCClient* client, Mapper* slave_mapper) {
	OSDMenuPrivate* priv = get_private(mnu);
	priv->client = client;
	if (slave_mapper == NULL) {
		priv->slave_mapper = create_slave_mapper(client, mnu);
		if (priv->slave_mapper == NULL)
			return false;
	} else {
		priv->slave_mapper = slave_mapper;
	}
	return true;
}

void osd_menu_connect(OSDMenu* mnu) {
	OSDMenuPrivate* priv = get_private(mnu);
	SCCClient* client = sccc_connect();
	if (client == NULL) {
		LERROR("Failed to connect to scc-daemon");
		osd_window_exit(OSD_WINDOW(mnu), 2);
		return;
	}
	
	priv->slave_mapper = create_slave_mapper(client, mnu);
	if (priv->slave_mapper == NULL) {
		// OOM
		RC_REL(client);
		osd_window_exit(OSD_WINDOW(mnu), 4);
		return;
	}
	
	priv->client = client;
	priv->client->userdata = mnu;
	priv->client->callbacks.on_ready = &osd_menu_connection_ready;
	priv->client->callbacks.on_event = &osd_menu_on_event;
	priv->client->callbacks.on_reconfigured = &osd_menu_on_reconfigured;
	GSource* src = scc_gio_client_to_gsource(client);
	g_source_set_callback(src, (GSourceFunc)osd_menu_on_data_ready, mnu, NULL);
}


struct osd_menu_release_data {
	Action*			action;
	OSDMenu*		mnu;
};

static gboolean osd_menu_dummy(gpointer ptr) {
	return FALSE;
}

static void osd_menu_release(gpointer ptr) {
	struct osd_menu_release_data* data = ptr;
	
	OSDMenuPrivate* priv = get_private(data->mnu);
	data->action->button_release(data->action, priv->slave_mapper);
	g_object_unref(data->mnu);
	RC_REL(data->action);
	free(data);
}


void osd_menu_confirm(OSDMenu* mnu) {
	OSDMenuPrivate* priv = get_private(mnu);
	char* filename = NULL;
	MenuItem* i = NULL;
	if (priv->selected != NULL)
		i = g_object_get_data(G_OBJECT(priv->selected), "scc-menu-item-data");
	
	if (i == NULL) return;
	switch (i->type) {
	case MI_ACTION: {
		struct osd_menu_release_data* data;
		data = malloc(sizeof(struct osd_menu_release_data));
		ASSERT(data != NULL);
		data->action = i->action;
		data->mnu = mnu;
		RC_ADD(data->action);
		g_object_ref(data->mnu);
		scc_action_compress(&data->action);
		data->action->button_press(data->action, priv->slave_mapper);
		g_idle_add_full(G_PRIORITY_DEFAULT_IDLE, osd_menu_dummy, data, osd_menu_release);
		osd_window_exit(OSD_WINDOW(mnu), 0);
		break;
	}
	case MI_SUBMENU: {
		filename = scc_find_menu(i->submenu);
		if (filename != NULL) {
			DDEBUG("Opening submenu '%s'", filename);
			OSDMenu* child = osd_menu_new(filename, &priv->settings);
			free(filename);
			if (child != NULL) {
				priv->child = child;
				g_signal_connect(G_OBJECT(child), "exit", (GCallback)&on_mnu_child_exit, mnu);
				g_signal_connect(G_OBJECT(child), "ready", (GCallback)&on_mnu_child_ready, mnu);
				ivec_t pos = osd_window_get_position(OSD_WINDOW(mnu));
				pos.x += (pos.x < 0) ? -SUBMENU_OFFSET : SUBMENU_OFFSET;
				pos.y += (pos.y < 0) ? -SUBMENU_OFFSET : SUBMENU_OFFSET;
				osd_window_set_position(OSD_WINDOW(child), pos.x, pos.y);
				osd_menu_set_client(child, priv->client, priv->slave_mapper);
				g_signal_emit_by_name(G_OBJECT(child), "ready");
			}
		}
		break;
	}
	default:
		break;
	}
}


static void osd_menu_init(OSDMenu* mnu) {
	OSDMenuPrivate* priv = get_private(mnu);
	priv->sc = NULL;
	priv->data = NULL;
	priv->client = NULL;
	priv->selected = NULL;
}


extlib_t osd_menu_load_plugin(const char* name) {
	char error[256];
	extlib_t plugin = scc_load_library(SCLT_OSD_MENU_PLUGIN, "libscc-osd-menu-", name, error);
	if (plugin == NULL) {
		LERROR("Failed to load menu plugin: %s", error);
		return NULL;
	}
	return plugin;
}


void osd_menu_set_plugin_data(OSDMenu* mnu, void* data) {
	OSDMenuPrivate* priv = get_private(mnu);
	priv->plugin_data = data;
}


void* osd_menu_get_plugin_data(OSDMenu* mnu) {
	OSDMenuPrivate* priv = get_private(mnu);
	return priv->plugin_data;
}


MenuData* osd_menu_get_menu_data(OSDMenu* mnu) {
	OSDMenuPrivate* priv = get_private(mnu);
	return priv->data;
}

MenuItem* osd_menu_get_selected(OSDMenu* mnu) {
	OSDMenuPrivate* priv = get_private(mnu);
	if (priv->selected == NULL)
		return NULL;
	MenuItem* i = g_object_get_data(G_OBJECT(priv->selected), "scc-menu-item-data");
	return i;
}


static void osd_menu_finalize(GObject* _mnu) {
	OSDMenu* mnu = OSD_MENU(_mnu);
	OSDMenuPrivate* priv = get_private(mnu);
	if (priv->plugin_data != NULL) {
		osd_menu_free_plugin_data_fn osd_menu_free_plugin_data;
		osd_menu_free_plugin_data = scc_load_function(priv->plugin,
				"osd_menu_free_plugin_data", NULL);
		if (osd_menu_free_plugin_data == NULL) {
			WARN("plugin data set, but osd_menu_free_plugin_data function not defined in plugin, we are leaking some data");
		} else {
			osd_menu_free_plugin_data(mnu, priv->plugin_data);
		}
	}
}


bool osd_menu_parse_args(int argc, char** argv, const char** usage, OSDMenuSettings* settings) {
	settings->plugin_name = NULL;
	settings->filename = NULL;
	settings->menu_name = NULL;
	settings->size = 1;
	settings->icon_size = 1.0;
	settings->controller_id = NULL;
	settings->control_with = PST_STICK;
	settings->confirm_with = B_A;
	settings->cancel_with = B_B;
	settings->use_cursor = false;
	
	char* control_with = NULL;
	char* confirm_with = NULL;
	char* cancel_with = NULL;
	struct argparse_option options[] = {
		OPT_HELP(),
		OPT_GROUP("Basic options"),
		OPT_STRING('f', "from-file", &settings->filename, "load menu from json file (full or relative path)"),
		OPT_STRING('m', "from-menu", &settings->menu_name, "load menu from json file (name that will be searched in menu directories)"),
		OPT_STRING('t', "type", &settings->plugin_name, "menu type (plugin) to use. Available types: 'vmenu' (default), 'hmenu'"),
		OPT_STRING('c', "control-with", &control_with, "sets which pad or stick should be used to navigate menu. Defaults to STICK"),
		OPT_STRING(0, "confirm-with", &confirm_with, "button used to confirm choice. Defaults to A"),
		OPT_STRING(0, "cancel-with", &cancel_with, "button used to cancel menu. Defaults to B"),
		OPT_BOOLEAN('u', "use-cursor", &settings->use_cursor, "display and use cursor to navigate menu"),
		OPT_INTEGER(0, "size", &settings->size, "Menu size (icon size). Defaults to 1"),
		OPT_FLOAT(0, "icon-size", &settings->icon_size, "Icon size. Defaults to 1"),
		OPT_END(),
	};
	struct argparse argparse;
	argparse_init(&argparse, options, usage, 0);
	argparse_describe(&argparse, "\nDisplays on-screen menu", NULL);
	argc = argparse_parse(&argparse, argc, (const char**)argv);
	if (argc < 0)
		return (argc == -5);
	
	if ((settings->filename == NULL) && (settings->menu_name == NULL)) {
		argparse_usage(&argparse);
		return false;
	}
	if (settings->plugin_name == NULL)
		settings->plugin_name = "vmenu";
	if (control_with != NULL) {
		settings->control_with = scc_string_to_pst(control_with);
		if (strcmp(control_with, "DEFAULT") == 0) {
			settings->control_with = PST_STICK;
		} else if ((settings->control_with == 0)
					|| (settings->control_with == PST_LTRIGGER)
					|| (settings->control_with == PST_RTRIGGER)) {
			LERROR("Invalid value for '--control-with' option: '%s'", control_with);
			return false;
		}
	}
	if (confirm_with != NULL) {
		settings->confirm_with = scc_string_to_button(confirm_with);
		if (strcmp(confirm_with, "DEFAULT") == 0) {
			settings->confirm_with = scc_what_to_pressed_button(settings->control_with);
			if (settings->confirm_with == 0)
				// TODO: Actual DEFAULTs from config here?
				settings->confirm_with = B_A;
		} else if (strcmp(confirm_with, "SAME") == 0) {
			settings->confirm_with = scc_what_to_touch_button(settings->control_with);
		} else if (strcmp(confirm_with, "ALWAYS") == 0) {
			settings->confirm_with = SCC_ALWAYS;
		} else if (settings->confirm_with == 0) {
			LERROR("Invalid value for '--confirm-with' option: '%s'", confirm_with);
			return false;
		}
	}
	if (cancel_with != NULL) {
		settings->cancel_with = scc_string_to_button(cancel_with);
		if (strcmp(cancel_with, "DEFAULT") == 0) {
			if (settings->control_with == PST_LPAD)
				settings->cancel_with = B_LPADTOUCH;
			else if (settings->control_with == PST_RPAD)
				settings->cancel_with = B_RPADTOUCH;
			else
				// TODO: Actual DEFAULTs from config here?
				settings->cancel_with = B_B;
			if (settings->cancel_with == settings->confirm_with) {
				// Special case, would create un-cancelable menu
				settings->cancel_with = B_B;
			}
		} if (strcmp(cancel_with, "SAME") == 0) {
			settings->cancel_with = scc_what_to_touch_button(settings->control_with);
		} else if (settings->cancel_with == 0) {
			LERROR("Invalid value for '--cancel-with' option: '%s'", cancel_with);
			return false;
		}
	}
	return true;
}

OSDMenu* osd_menu_new(const char* filename, const OSDMenuSettings* settings) {
	extlib_t plugin = osd_menu_load_plugin(settings->plugin_name);
	if (plugin == NULL) return NULL;
	osd_menu_create_widgets_fn osd_menu_create_widgets = scc_load_function(plugin, "osd_menu_create_widgets", NULL);
	ASSERT(osd_menu_create_widgets != NULL);
	
	int err;
	Config* cfg = config_load();
	if (cfg == NULL) {
		LERROR("Failed load configuration");
		return NULL;
	}
	MenuData* data;
	if (filename != NULL) {
		data = scc_menudata_from_json(filename, &err);
	} else if (settings->menu_name != NULL) {
		char* filename = scc_find_menu(settings->menu_name);
		if (filename == NULL) {
			LERROR("Menu '%s' not found", settings->menu_name);
			RC_REL(cfg);
			return NULL;
		}
		data = scc_menudata_from_json(filename, &err);
		free(filename);
	} else {
		LERROR("No source for menu specified");
		RC_REL(cfg);
		return NULL;
	}
	if (data == NULL) {
		LERROR("Failed to decode menu");
		RC_REL(cfg);
		return NULL;
	}
	scc_menudata_apply_generators(data, cfg);
	RC_REL(cfg);
	
	const OSDWindowCallbacks callbacks = {};
	GtkWidget* o = g_object_new(OSD_MENU_TYPE, GTK_WINDOW_TOPLEVEL, NULL);
	osd_window_setup(OSD_WINDOW(o), "osd-menu", callbacks);
	OSDMenu* mnu = OSD_MENU(o);
	OSDMenuPrivate* priv = get_private(mnu);
	
	priv->handle_input_cb = scc_load_function(plugin, "osd_menu_handle_input", NULL);
	if (priv->handle_input_cb == NULL) {
		priv->handle_stick_cb = scc_load_function(plugin, "osd_menu_handle_stick", NULL);
		if (priv->handle_stick_cb == NULL) {
			priv->sc = NULL;
		} else {
			priv->sc = stick_controller_create(_osd_menu_handle_stick, mnu);
			ASSERT(priv->sc != NULL);
		}
	} else {
		priv->handle_stick_cb = NULL;
	}
	
	priv->data = data;
	priv->client = NULL;
	priv->cursor = NULL;
	priv->fixed = NULL;
	priv->selected = NULL;
	priv->plugin = plugin;
	priv->plugin_data = NULL;
	priv->slave_mapper = NULL;
	priv->settings = *settings;
	
	GtkWidget* parent = osd_menu_create_widgets(mnu, &priv->settings);
	gtk_widget_set_name(parent, "osd-menu");
	
	if (priv->handle_input_cb != NULL) {
		gtk_container_add(GTK_CONTAINER(mnu), parent);
	} else if (priv->settings.use_cursor) {
		StrBuilder* sb = strbuilder_new();
		ASSERT(sb != NULL);
		strbuilder_add(sb, scc_get_share_path());
		strbuilder_add_path(sb, "images");
		strbuilder_add_path(sb, "menu-cursor.svg");
		ASSERT(!strbuilder_failed(sb));
		priv->cursor = gtk_image_new_from_file(strbuilder_get_value(sb));
		strbuilder_free(sb);
		ASSERT(priv->cursor != NULL);
		
		priv->fixed = gtk_fixed_new();
		gtk_container_add(GTK_CONTAINER(mnu), priv->fixed);
		gtk_container_add(GTK_CONTAINER(priv->fixed), parent);
		gtk_container_add(GTK_CONTAINER(priv->fixed), priv->cursor);
	} else {
		if (!osd_menu_select_index(mnu, 0))
			osd_menu_next_item(mnu, 1);
		gtk_container_add(GTK_CONTAINER(mnu), parent);
	}
	
	return mnu;
}

