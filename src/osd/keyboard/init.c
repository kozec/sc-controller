#define LOG_TAG "OSD"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/osd/osd_keyboard.h"
#include "scc/osd/osd_window.h"
#include <glib.h> // glib.h has to be included before client.h
#include "scc/virtual_device.h"
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
	
	if (!sccc_lock(c, handle, "LEFT", "RIGHT", "STICK", "A", "B", "X", "Y",
					"LB", "RB", "LT", "RT", "LGRIP", "RGRIP", "C")) {
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

static void osd_keyboard_init(OSDKeyboard* kbd) {
	OSDKeyboardPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(kbd, OSD_KEYBOARD_TYPE, OSDKeyboardPrivate);
	priv->buttons = list_new(Button, 0);
	ASSERT(priv->buttons);
	priv->client = NULL;
	priv->controller_id = NULL;
}


OSDKeyboard* osd_keyboard_new(const char* filename) {
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
	ASSERT(priv->slave_mapper);
	priv->client = client;
	priv->client->userdata = kbd;
	priv->client->on_ready = &osd_keyboard_on_connection_ready;
	priv->client->on_event = &osd_keyboard_on_event;
	
	sccc_slave_mapper_set_devices(priv->slave_mapper,
			scc_virtual_device_create(VTP_KEYBOARD, NULL),
			NULL);
	
	int err;
	char* osd_kbd_pro = scc_find_profile(".scc-osd.keyboard");
	Profile* profile = (filename == NULL) ? NULL : scc_profile_from_json(osd_kbd_pro, &err);
	free(osd_kbd_pro);
	if ((profile == NULL) || !load_keyboard_data(filename, priv)) {
		RC_REL(profile);
		osd_window_exit(OSD_WINDOW(kbd), 1);
		return NULL;
	}
	priv->slave_mapper->set_profile(priv->slave_mapper, profile, false);
	RC_REL(profile);
	
	GSource* src = scc_gio_client_to_gsource(client);
	g_source_set_callback(src, (GSourceFunc)osd_keyboard_on_data_ready, kbd, NULL);
	
	if (!init_display(kbd, priv))
		// TODO: Do I need to deallocate something here?
		return NULL;
	
	return kbd;
}

