#define LOG_TAG "OSD"
#include "scc/utils/strbuilder.h"
#include "scc/utils/argparse.h"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/osd/osd_keyboard.h"
#include "scc/osd/osd_window.h"
#include <glib.h> // glib.h has to be included before client.h
#include "scc/virtual_device.h"
#include "scc/special_action.h"
#include "scc/profile.h"
#include "scc/client.h"
#include "scc/tools.h"
#include "keyboard.h"

struct _OSDKeyboard {
	GtkWindow				parent;
	OSDKeyboardPrivate*		priv;
};

struct _OSDKeyboardClass {
	GtkWindowClass			parent_class;
};

G_DEFINE_TYPE_WITH_CODE(OSDKeyboard, osd_keyboard, OSD_WINDOW_TYPE, G_ADD_PRIVATE(OSDKeyboard));

static void osd_keyboard_class_init(OSDKeyboardClass *klass) { }

static void osd_keyboard_on_connection_ready(SCCClient* c) {
	OSDKeyboard* kbd = OSD_KEYBOARD(c->userdata);
	OSDKeyboardPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(kbd, OSD_KEYBOARD_TYPE, OSDKeyboardPrivate);
	uint32_t handle = sccc_get_controller_handle(c, priv->controller_id);
	if (handle == 0) {
		if (priv->controller_id == NULL)
			LERROR("There is no controller connected");
		else
			LERROR("Requested controller '%s' not connected", priv->controller_id);
		g_signal_emit_by_name(G_OBJECT(kbd), "exit", 4);
		return;
	}
	
	if (!sccc_lock(c, handle,
					"STICK", "A", "B", "X", "Y", "C", "LGRIP", "RGRIP",
					"START", "BACK", "LB", "RB", "LTRIGGER", "RTRIGGER",
					"LPAD", "RPAD", "LPADPRESS", "RPADPRESS")) {
		LERROR("Failed to lock controller");
		g_signal_emit_by_name(G_OBJECT(kbd), "exit", 3);
		return;
	}
	
	g_signal_emit_by_name(G_OBJECT(kbd), "ready");
}

static void osd_keyboard_on_event(SCCClient* c, uint32_t handle, SCButton button, PadStickTrigger pst, int values[]) {
	OSDKeyboard* kbd = OSD_KEYBOARD(c->userdata);
	OSDKeyboardPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(kbd, OSD_KEYBOARD_TYPE, OSDKeyboardPrivate);
	sccc_slave_mapper_feed(priv->slave_mapper, button, pst, values);
	// else
	// 	LOG("# %i %i %i > %i %i", handle, button, pst, values[0], values[1]);
}

static gboolean osd_keyboard_on_data_ready(GIOChannel* source, GIOCondition condition, gpointer _kbd) {
	OSDKeyboard* kbd = OSD_KEYBOARD(_kbd);
	OSDKeyboardPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(kbd, OSD_KEYBOARD_TYPE, OSDKeyboardPrivate);
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

static void osd_keyboard_stick(int dx, int dy, void* userdata) {
	// OSDKeyboard* kbd = OSD_KEYBOARD(userdata);
	LOG("STICK: %i %i", dx, dy);
}

bool is_button_under_cursor(OSDKeyboardPrivate* priv, int index, struct Button* b) {
	return (
		(priv->cursors[index].position.x >= b->pos.x)
		&& (priv->cursors[index].position.x < b->pos.x + b->size.x)
		&& (priv->cursors[index].position.y >= b->pos.y)
		&& (priv->cursors[index].position.y < b->pos.y + b->size.y)
	);
}

static void osd_keyboard_set_cursor_position(OSDKeyboard* kbd, int index, AxisValue _x, AxisValue _y) {
	OSDKeyboardPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(kbd, OSD_KEYBOARD_TYPE, OSDKeyboardPrivate);
	if ((index < 0) || (index > 1)) return;
	
	double w = priv->limits[index].x1 - priv->limits[index].x0;
	double h = priv->limits[index].y1 - priv->limits[index].y0;
	double x = (double)_x / (double)(STICK_PAD_MAX);
	double y = (double)_y / (double)(STICK_PAD_MAX) * -1.0;
	
	circle_to_square(&x, &y);
	x = clamp(
		0,
		(priv->limits[index].x0 + w * 0.5) + x * w * 0.5,
		priv->limits[index].x1
	);
	y = clamp(
		0,
		(priv->limits[index].y0 + h * 0.5) + y * h * 0.5,
		priv->limits[index].y1 - 0
	);
	
	vec_set(priv->cursors[index].position, x, y);
	gtk_widget_queue_draw(GTK_WIDGET(kbd));
}

static void osd_keyboard_set_cursor_pressed(Mapper* m, OSDKeyboard* kbd, int index, bool pressed) {
	OSDKeyboardPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(kbd, OSD_KEYBOARD_TYPE, OSDKeyboardPrivate);
	if ((index < 0) || (index > 1)) return;
	if (pressed) {
		FOREACH_IN(Button*, b, priv->buttons) {
			if (is_button_under_cursor(priv, index, b)) {
				if (priv->cursors[index].pressed_button_index != b->index) {
					Action* a = b->action;
					priv->cursors[index].pressed_button_index = b->index;
					a->button_press(a, m);
				}
				break;
			}
		}
	} else {
		if (priv->cursors[index].pressed_button_index != -1) {
			Button* b = list_get(priv->buttons, priv->cursors[index].pressed_button_index);
			Action* a = b->action;
			a->button_release(a, m);
		}
		priv->cursors[index].pressed_button_index = -1;
	}
	gtk_widget_queue_draw(GTK_WIDGET(kbd));
}

static bool osd_keyboard_sa_handler(Mapper* m, unsigned int sa_action_type, void* sa_data) {
	if (sa_action_type != SAT_APP_DEFINED)
		return false;
	
	SAAppDefinedActionData* data = (SAAppDefinedActionData*)sa_data;
	OSDKeyboard* kbd = OSD_KEYBOARD(sccc_slave_mapper_get_userdata(m));
	
	if (data->keyword == KW_OSK_CURSOR) {
		AxisValue* values = (AxisValue*)(data->data);
		osd_keyboard_set_cursor_position(kbd, values[0], values[1], values[2]);
	} else if (data->keyword == KW_OSK_PRESS) {
		AxisValue* values = (AxisValue*)(data->data);
		osd_keyboard_set_cursor_pressed(m, kbd, values[0], values[1]);
	} else if (data->keyword == KW_OSK_CLOSE) {
		// TODO: Closing when called from osd daemon
		exit(0);
	}
	return false;
}


static void osd_keyboard_init(OSDKeyboard* kbd) {
	OSDKeyboardPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(kbd, OSD_KEYBOARD_TYPE, OSDKeyboardPrivate);
	memset(priv, 0, sizeof(OSDKeyboardPrivate));
	priv->buttons = list_new(Button, 0);
	priv->help_lines = list_new(HelpLine, 9);
	ASSERT(priv->buttons);
	ASSERT(priv->help_lines);
	list_set_dealloc_cb(priv->help_lines, free);
	priv->client = NULL;
	priv->controller_id = NULL;
	register_keyboard_actions();
}

static const char *const usage[] = {
	"scc-osd-keyboard -f <filename>",
	NULL,
};

int osd_keyboard_parse_args(OSDKeyboardOptions* options, int argc, char** argv) {
	struct argparse_option argopts[] = {
		OPT_HELP(),
		OPT_GROUP("Basic options"),
		OPT_STRING('f', NULL, &options->filename, "keyboard definition file to use"),
		OPT_END(),
	};
	options->filename = NULL;
	struct argparse argparse;
	argparse_init(&argparse, argopts, usage, 0);
	argparse_describe(&argparse, "\nDisplays on-screen keyboard", NULL);
	argc = argparse_parse(&argparse, argc, (const char**)argv);
	if (argc < 0)
		return -1;
	if (options->filename == NULL) {
		options->filename = strbuilder_fmt("%s/keyboard.json", scc_get_share_path());
		ASSERT(options->filename != NULL);
	}
	return 0;
}


OSDKeyboard* osd_keyboard_new(OSDKeyboardOptions* options) {
	SCCClient* client = sccc_connect();
	if (client == NULL) {
		LERROR("Failed to connect to scc-daemon");
		return NULL;
	}
	
	const OSDWindowCallbacks callbacks = {};
	GtkWidget* o = g_object_new(OSD_KEYBOARD_TYPE, GTK_WINDOW_TOPLEVEL, NULL);
	osd_window_setup(OSD_WINDOW(o), "osd-keyboard", callbacks);
	OSDKeyboard* kbd = OSD_KEYBOARD(o);
	OSDKeyboardPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(kbd, OSD_KEYBOARD_TYPE, OSDKeyboardPrivate);
	
	vec_set(priv->size, 10, 10);
	priv->slave_mapper = sccc_slave_mapper_new(client);
	if (priv->slave_mapper == NULL)
		goto osd_keyboard_new_failed;
	sccc_slave_mapper_set_userdata(priv->slave_mapper, kbd);
	sccc_slave_mapper_set_sa_handler(priv->slave_mapper, osd_keyboard_sa_handler);
	
	priv->client = client;
	priv->client->userdata = kbd;
	priv->client->callbacks.on_ready = &osd_keyboard_on_connection_ready;
	priv->client->callbacks.on_event = &osd_keyboard_on_event;
	
	sccc_slave_mapper_set_devices(priv->slave_mapper,
			scc_virtual_device_create(VTP_KEYBOARD, NULL),
			NULL);
	
	int err;
	char* osd_kbd_pro = scc_find_profile(".scc-osd.keyboard");
	Profile* profile = scc_profile_from_json(osd_kbd_pro, &err);
	free(osd_kbd_pro);
	if ((profile == NULL) || !load_keyboard_data(options->filename, priv)) {
		RC_REL(profile);
		osd_window_exit(OSD_WINDOW(kbd), 1);
		goto osd_keyboard_new_failed;
	}
	priv->slave_mapper->set_profile(priv->slave_mapper, profile, false);
	RC_REL(profile);
	
	priv->client_src = scc_gio_client_to_gsource(client);
	g_source_set_callback(priv->client_src,
			(GSourceFunc)osd_keyboard_on_data_ready, kbd, NULL);
	
	if (!init_display(kbd, priv))
		// TODO: Do I need to deallocate something here?
		goto osd_keyboard_new_failed;
	
	osd_keyboard_set_cursor_position(kbd, 0, 0, 0);
	osd_keyboard_set_cursor_position(kbd, 1, 0, 0);
	priv->cursors[0].pressed_button_index = -1;
	priv->cursors[1].pressed_button_index = -1;
	generate_help_lines(priv);
	return kbd;

osd_keyboard_new_failed:
	if (priv->slave_mapper != NULL)
		sccc_slave_mapper_free(priv->slave_mapper, true);
	if (priv->client_src != NULL)
		g_source_unref(priv->client_src);
	RC_REL(priv->client);
	return NULL;
}

