#define LOG_TAG "OSDD"
#include "scc/utils/logging.h"
#include "scc/utils/traceback.h"
#include "scc/utils/argparse.h"
#include "scc/utils/assert.h"
#include "scc/osd/osd_keyboard.h"
#include "scc/osd/osd_menu.h"
#include "scc/client.h"
#include "scc/tools.h"
#include "osd.h"
#include <gtk/gtk.h>

static OSDMenu* current_menu = NULL;
static SCCClient* client;
static int exit_code = 0;


static void on_mnu_ready(void* _mnu) {
	gtk_widget_show_all(GTK_WIDGET(_mnu));
}

static void on_mnu_exit(void* _mnu) {
	if (current_menu == _mnu) {
		gtk_widget_destroy(GTK_WIDGET(_mnu));
		current_menu = NULL;
		sccc_unlock_all(client);
	}
}

static void display_menu(StringList argv) {
	static const char *const usage[] = { NULL };
	OSDMenuSettings settings;
	if (current_menu != NULL) {
		WARN("Menu is already visible, cannot show another one");
		return;
	}
	if (!osd_menu_parse_args(list_len(argv), argv->items, NULL, &settings))
		return;
	OSDMenu* mnu = osd_menu_new(NULL, &settings);
	if (mnu == NULL)
		return;
	g_signal_connect(G_OBJECT(mnu), "exit", (GCallback)&on_mnu_exit, NULL);
	g_signal_connect(G_OBJECT(mnu), "ready", (GCallback)&on_mnu_ready, NULL);
	if (!osd_menu_set_client(mnu, client, NULL)) {
		LERROR("OOM while trying to show menu");
		on_mnu_exit(mnu);
	}
	osd_menu_lock_inputs(mnu);
	current_menu = mnu;
	// osd_menu_connect(mnu);
	// gtk_main();
}

static void on_event(SCCClient* c, uint32_t handle, SCButton button,
			PadStickTrigger pst, int values[]) {
	if (current_menu != NULL)
		osd_menu_parse_event(current_menu, c, handle, button, pst, values);
}

static gboolean on_data_ready(GIOChannel* source, GIOCondition condition, void* trash) {
	const char* message = sccc_recieve(client);
	if (message != NULL) {
		if (message[0] == 0) {
			// Disconnected
			LERROR("Connection to daemon closed");
			exit_code = 1;
			gtk_main_quit();
			return true;
		}
		if (strstr(message, "OSD:") == message) {
			StringList argv = sccc_parse(message);
			if (argv == NULL) {
				LERROR("OOM while parsing message from daemon");
				exit(1);
			}
			free(list_unshift(argv));
			if (0 == strcmp("menu", list_get(argv, 0))) {
				display_menu(argv);
			}
		}
	}
	return true;
}


inline static bool register_with_sccd() {
	int32_t rid = sccc_request(client, "Register: osd");
	const char* response = sccc_get_response(client, rid);
	return 0 == strcmp("OK.", response);
}

int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	gtk_init(&argc, &argv);
	
	client = sccc_connect();
	if (client == NULL) {
		LERROR("Failed to connect to scc-daemon");
		return 2;
	}
	
	if (!register_with_sccd()) {
		LERROR("Failed to register with scc-daemon");
		return 2;
	}
	
	client->callbacks.on_event = &on_event;
	GSource* src = scc_gio_client_to_gsource(client);
	g_source_set_callback(src, (GSourceFunc)on_data_ready, NULL, NULL);
	gtk_main();
	
	return exit_code;
}

