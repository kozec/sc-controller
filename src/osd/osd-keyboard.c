#include "scc/utils/strbuilder.h"
#include "scc/utils/traceback.h"
#include "scc/utils/iterable.h"
#include "scc/utils/argparse.h"
#include "scc/utils/assert.h"
#include "scc/osd/osd_keyboard.h"
#include "scc/tools.h"
#include <gtk/gtk.h>

static const char *const usage[] = {
	"scc-osd-keyboard -f <filename>",
	NULL,
};

static void on_mnu_exit(void* _kbd, int code) {
	exit(code);
}

static void on_mnu_ready(void* _kbd) {
	gtk_widget_show_all(GTK_WIDGET(_kbd));
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	gtk_init(&argc, &argv);
	
	char* filename = NULL;
	struct argparse_option options[] = {
		OPT_HELP(),
		OPT_GROUP("Basic options"),
		OPT_STRING('f', NULL, &filename, "keyboard definition file to use"),
		OPT_END(),
	};
	struct argparse argparse;
	argparse_init(&argparse, options, usage, 0);
	argparse_describe(&argparse, "\nDisplays on-screen keyboard", NULL);
	argc = argparse_parse(&argparse, argc, (const char**)argv);
	if (argc < 0)
		return 1;
	if (filename == NULL) {
		filename = strbuilder_fmt("%s/keyboard.json", scc_get_share_path());
		ASSERT(filename != NULL);
	}
	
	OSDKeyboard* keyboard = osd_keyboard_new(filename);
	g_signal_connect(G_OBJECT(keyboard), "exit", (GCallback)&on_mnu_exit, NULL);
	g_signal_connect(G_OBJECT(keyboard), "ready", (GCallback)&on_mnu_ready, NULL);
	if (keyboard != NULL) {
		gtk_main();
		return 0;
	} else {
		return 1;
	}
}
