#include "scc/utils/traceback.h"
#include "scc/utils/assert.h"
#include "scc/osd/osd_keyboard.h"
#include "scc/tools.h"
#include <gtk/gtk.h>

static void on_mnu_exit(void* _kbd, int code) {
	exit(code);
}

static void on_mnu_ready(void* _kbd) {
	gtk_widget_show_all(GTK_WIDGET(_kbd));
}


int main(int argc, char** argv) {
	OSDKeyboardOptions options;
	traceback_set_argv0(argv[0]);
	gtk_init(&argc, &argv);
	
	if (osd_keyboard_parse_args(&options, argc, argv) < 0)
		return 1;
	OSDKeyboard* keyboard = osd_keyboard_new(&options);
	
	g_signal_connect(G_OBJECT(keyboard), "exit", (GCallback)&on_mnu_exit, NULL);
	g_signal_connect(G_OBJECT(keyboard), "ready", (GCallback)&on_mnu_ready, NULL);
	if (keyboard != NULL) {
		gtk_main();
		return 0;
	} else {
		return 1;
	}
}

