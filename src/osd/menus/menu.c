#define LOG_TAG "OSD"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
#include "scc/osd/osd_window.h"
#include "scc/osd/osd_menu.h"
#include "scc/osd/menu_icon.h"
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

#define SUBMENU_OFFSET	20

typedef struct _OSDMenuPrivate		OSDMenuPrivate;

struct _OSDMenu {
	GtkWindow			parent;
	OSDMenuPrivate*		priv;
};

struct _OSDMenuClass {
	GtkWindowClass		parent_class;
};

struct _OSDMenuPrivate {
	StickController*	sc;
	MenuData*			data;
	SCCClient*			client;
	GtkWidget*			selected;
	OSDMenu*			child;
	Mapper*				slave_mapper;
	const char*			controller_id;	// NULL for "take 1st available"
	PadStickTrigger		control_with;
	SCButton			confirm_with;
	SCButton			cancel_with;
};

G_DEFINE_TYPE_WITH_CODE(OSDMenu, osd_menu, OSD_WINDOW_TYPE, G_ADD_PRIVATE(OSDMenu));

static void osd_menu_item_selected(OSDMenu* mnu);

static void osd_menu_class_init(OSDMenuClass *klass) { }

static void align_cb(GtkWidget* w, void* align) {
	if (G_OBJECT_TYPE(w) == GTK_TYPE_LABEL)
		gtk_label_set_xalign(GTK_LABEL(w), *(gfloat*)align);
}

static GtkWidget* make_menu_row(const char* label, const char* icon, bool is_submenu) {
	bool has_colors;
	GtkWidget* w_icon = NULL;
	if (icon != NULL) {	
		char* filename = scc_find_icon(icon, false, &has_colors, NULL, NULL);
		if (filename != NULL) {
			w_icon = GTK_WIDGET(menu_icon_new(filename, has_colors));
			free(filename);
		}
	}
	GtkWidget* label1 = gtk_label_new(label);
	GtkWidget* label2 = is_submenu ? gtk_label_new(">>") : NULL;
	GtkWidget* box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
	GtkWidget* button = gtk_button_new();
	gtk_label_set_xalign(GTK_LABEL(label1), 0.0);
	if (w_icon != NULL) {
		gtk_box_pack_start(GTK_BOX(box), w_icon, false, true, 0);
		gtk_box_pack_start(GTK_BOX(box), label1, true, true, 10);
		gtk_widget_set_name(GTK_WIDGET(w_icon), "icon");
	} else {
		gtk_box_pack_start(GTK_BOX(box), label1, true, true, 1);
	}
	if (label2 != NULL) {
		gtk_widget_set_margin_start(label2, 30);
		gtk_label_set_xalign(GTK_LABEL(label2), 1.0);
		gtk_box_pack_start(GTK_BOX(box), label2, false, true, 1);
	}
	gtk_container_add(GTK_CONTAINER(button), box);
	gtk_button_set_relief(GTK_BUTTON(button), GTK_RELIEF_NONE);
	return button;
}

static GtkWidget* make_widget(MenuItem* i) {
	GtkWidget* w;
	gfloat center = 0.5;
	switch (i->type) {
	case MI_DUMMY:
	case MI_ACTION:
		if (i->name == NULL) {
			// TODO: Use description instead
			if (i->action == NULL)
				return NULL;
			char* label = scc_action_to_string(i->action);
			ASSERT(label != NULL);
			w = make_menu_row(label, i->icon, false);
			free(label);
		} else {
			w = make_menu_row(i->name, i->icon, false);
		}
		if (i->type == MI_DUMMY)
			gtk_widget_set_name(w, "osd-menu-dummy");
		else
			gtk_widget_set_name(w, "osd-menu-item");
		break;
	case MI_SUBMENU: {
		if (i->submenu == NULL)
			// Shouldn't be possible
			return NULL;
		if (i->name == NULL) {
			char* name = scc_path_strip_extension(i->submenu);
			ASSERT(name != NULL);
			w = make_menu_row(name, i->icon, true);
			free(name);
		} else {
			w = make_menu_row(i->name == NULL ? i->submenu : i->name, i->icon, true);
		}
		gtk_widget_set_name(GTK_WIDGET(w), "osd-menu-item");
		break;
	}
	case MI_SEPARATOR: {
		if (i->name != NULL) {
			w = gtk_button_new_with_label(i->name);
			gtk_button_set_relief(GTK_BUTTON(w), GTK_RELIEF_NONE);
			gtk_container_forall(GTK_CONTAINER(w), align_cb, &center);
		} else {
			w = gtk_separator_new(GTK_ORIENTATION_HORIZONTAL);
		}
		gtk_widget_set_name(GTK_WIDGET(w), "osd-menu-separator");
		break;
	}
	default:
		return NULL;
	}
	g_object_set_data(G_OBJECT(w), "scc-menu-item-data", i);
	return w;
}


static void on_mnu_child_exit(void* _child, int code, void* _mnu) {
	OSDMenu* mnu = (OSDMenu*)_mnu;
	OSDMenuPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
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
	OSDMenuPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
	const char* message = sccc_recieve(priv->client);
	if (message != NULL) {
		if (message[0] == 0)
			// Disconnected
			// TODO: Handle this
			return false;
		// if (message != NULL)
		// 	LOG("> %s", message);
	}
	// on_reconfigured
	return true;
}

static void osd_menu_connection_ready(SCCClient* c) {
	OSDMenu* mnu = OSD_MENU(c->userdata);
	OSDMenuPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
	uint32_t handle = sccc_get_controller_handle(c, priv->controller_id);
	if (handle == 0) {
		if (priv->controller_id == NULL)
			LERROR("There is no controller connected");
		else
			LERROR("Requested controller '%s' not connected", priv->controller_id);
		osd_window_exit(OSD_WINDOW(mnu), 4);
		return;
	}
	
	const char* control_with = scc_what_to_string(priv->control_with);
	const char* confirm_with = scc_button_to_string(priv->confirm_with);
	const char* cancel_with = scc_button_to_string(priv->cancel_with);
	if (!sccc_lock(c, handle, control_with, confirm_with, cancel_with)) {
		LERROR("Failed to lock controller");
		osd_window_exit(OSD_WINDOW(mnu), 3);
	}
	
	g_signal_emit_by_name(G_OBJECT(mnu), "ready");
}

static void osd_menu_parse_event(OSDMenu* mnu, SCCClient* c, uint32_t handle,
			SCButton button, PadStickTrigger pst, int values[]) {
	OSDMenuPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
	if (priv->child != NULL)
		return osd_menu_parse_event(priv->child, c, handle, button, pst, values);
	if (pst == priv->control_with)
		stick_controller_feed(priv->sc, values);
	else if ((button == priv->cancel_with) && (values[0]))
		osd_window_exit(OSD_WINDOW(mnu), -1);
	else if ((button == priv->confirm_with) && (values[0]))
		osd_menu_item_selected(mnu);
	// else
	// 	LOG("# %i %i %i > %i %i", handle, button, pst, values[0], values[1]);
}

static void osd_menu_on_event(SCCClient* c, uint32_t handle, SCButton button,
			PadStickTrigger pst, int values[]) {
	OSDMenu* mnu = OSD_MENU(c->userdata);
	return osd_menu_parse_event(mnu, c, handle, button, pst, values);
}

void osd_menu_next_item(OSDMenu* mnu, int direction);

static void osd_menu_stick(int dx, int dy, void* userdata) {
	OSDMenu* mnu = OSD_MENU(userdata);
	osd_menu_next_item(mnu, dy);
	// LOG("STICK: %i %i", dx, dy);
}

/** Returns false if item at index is not selectable */
bool osd_menu_select(OSDMenu* mnu, size_t index) {
	OSDMenuPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
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
		priv->selected = NULL;
	}
	
	MenuItem* i = scc_menudata_get_by_index(priv->data, index);
	if ((i == NULL) || (i->id == NULL) || ((i->type != MI_ACTION) && (i->type != MI_SUBMENU)))
		// Not selectable
		return false;
	
	// TODO: This. Also note that priv->selected is c
	// if old_selected != i
	// 	if self.feedback and self.controller:
	// 		self.controller.feedback(*self.feedback)
	
	priv->selected = i->userdata;
	StrBuilder* sb = strbuilder_new();
	ASSERT(sb != NULL);
	strbuilder_add(sb, gtk_widget_get_name(GTK_WIDGET(priv->selected)));
	strbuilder_add(sb, "-selected");
	ASSERT(!strbuilder_failed(sb));
	gtk_widget_set_name(GTK_WIDGET(priv->selected), strbuilder_get_value(sb));
	strbuilder_free(sb);
	// GLib.timeout_add(2, self._check_on_screen_position)
	return true;
}

/** Returns -1 if widget is not found */
int get_menuitem_index(MenuData* dt, GtkWidget* widget) {
	if (widget == NULL)
		return -1;
	for (int x=0; x<scc_menudata_len(dt); x++) {
		MenuItem* i = scc_menudata_get_by_index(dt, x);
		if (i->userdata == widget)
			return x;
	}
	return -1;
}

/** Selects either next or previous menu item */
void osd_menu_next_item(OSDMenu* mnu, int direction) {
	OSDMenuPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
	int start = get_menuitem_index(priv->data, priv->selected);
	int i = start + direction;
	while (1) {
		if (i == start) {
			// Cannot find valid menu item
			osd_menu_select(mnu, start);
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
		if (osd_menu_select(mnu, i)) {
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
			OSDMenuPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
			sccc_unlock_all(priv->client);
			const char* argv[] = { scc_osd_keyboard, NULL };
			scc_spawn(argv, 0);
		}
		return true;
	}
	return false;
}

/** Configures menu to use already connected client */
void osd_menu_set_client(OSDMenu* mnu, SCCClient* client, Mapper* slave_mapper) {
	OSDMenuPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
	priv->client = client;
	ASSERT(slave_mapper);
	priv->slave_mapper = slave_mapper;
	g_signal_emit_by_name(G_OBJECT(mnu), "ready");
}

/** Establishes connection to daemon. Emits 'ready' or 'exit' signal when done */
void osd_menu_connect(OSDMenu* mnu) {
	OSDMenuPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
	SCCClient* client = sccc_connect();
	if (client == NULL) {
		LERROR("Failed to connect to scc-daemon");
		osd_window_exit(OSD_WINDOW(mnu), 2);
		return;
	}
	
	priv->slave_mapper = sccc_slave_mapper_new(client);
	if (priv->slave_mapper == NULL) {
		// OOM
		RC_REL(client);
		osd_window_exit(OSD_WINDOW(mnu), 4);
		return;
	}
	sccc_slave_mapper_set_userdata(priv->slave_mapper, mnu);
	sccc_slave_mapper_set_sa_handler(priv->slave_mapper, osd_menu_sa_handler);
	
	priv->client = client;
	priv->client->userdata = mnu;
	priv->client->callbacks.on_ready = &osd_menu_connection_ready;
	priv->client->callbacks.on_event = &osd_menu_on_event;
	GSource* src = scc_gio_client_to_gsource(client);
	g_source_set_callback(src, (GSourceFunc)osd_menu_on_data_ready, mnu, NULL);
}

static void osd_menu_item_selected(OSDMenu* mnu) {
	OSDMenuPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
	char* filename = NULL;
	MenuItem* i = NULL;
	if (priv->selected != NULL)
		i = g_object_get_data(G_OBJECT(priv->selected), "scc-menu-item-data");
	
	if (i == NULL) return;
	switch (i->type) {
	case MI_ACTION: {
		Action* a = i->action;
		if (a == NULL) {
			WARN("Activated menu item with no action");
			break;
		}
		RC_ADD(a);
		scc_action_compress(&a);
		a->button_press(a, priv->slave_mapper);
		RC_REL(a);
		osd_window_exit(OSD_WINDOW(mnu), 0);
		break;
	}
	case MI_SUBMENU: {
		filename = scc_find_menu(i->submenu);
		if (filename != NULL) {
			DDEBUG("Opening submenu '%s'", filename);
			OSDMenu* child = osd_menu_new(filename);
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
			}
		}
		break;
	}
	default:
		break;
	}
}

static void osd_menu_init(OSDMenu* mnu) {
	OSDMenuPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
	priv->sc = NULL;
	priv->data = NULL;
	priv->client = NULL;
	priv->selected = NULL;
	priv->controller_id = NULL;
}

OSDMenu* osd_menu_new(const char* filename) {
	int err;
	Config* cfg = config_load();
	if (cfg == NULL) {
		LERROR("Failed load configuration");
		return NULL;
	}
	MenuData* data = scc_menudata_from_json(filename, &err);
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
	OSDMenuPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mnu, OSD_MENU_TYPE, OSDMenuPrivate);
	
	priv->sc = stick_controller_create(&osd_menu_stick, mnu);
	ASSERT(priv->sc != NULL);
		priv->data = data;
	priv->selected = NULL;
	priv->control_with = PST_STICK;
	priv->confirm_with = B_A;
	priv->cancel_with = B_B;
	priv->slave_mapper = NULL;
	priv->client = NULL;
	
	GtkWidget* v = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
	gtk_widget_set_name(GTK_WIDGET(v), "osd-menu");
	
	ListIterator it = iter_get(priv->data);
	FOREACH(MenuItem*, i, it) {
		GtkWidget* w = make_widget(i);
		if (w != NULL) {
			gtk_box_pack_start(GTK_BOX(v), w, false, true, 0);
			i->userdata = w;
		}
	}
	if (!osd_menu_select(mnu, 0))
		osd_menu_next_item(mnu, 1);
	
	gtk_container_add(GTK_CONTAINER(mnu), v);
	
	return mnu;
}
