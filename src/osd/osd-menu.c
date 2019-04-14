#include "scc/utils/logging.h"
#include "scc/utils/traceback.h"
#include "scc/utils/iterable.h"
#include "scc/utils/argparse.h"
#include "scc/utils/assert.h"
#include "scc/osd/osd_menu.h"
#include <gtk/gtk.h>

static const char *const usage[] = {
	"scc-osd-menu -f <filename>",
	NULL,
};

static void on_mnu_exit(void* _mnu, int code) {
	exit(code);
}

static void on_mnu_ready(void* _mnu) {
	gtk_widget_show_all(GTK_WIDGET(_mnu));
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	gtk_init(&argc, &argv);
	
	char* filename = NULL;
	struct argparse_option options[] = {
		OPT_HELP(),
		OPT_GROUP("Basic options"),
		OPT_STRING('f', "from-file", &filename, "load menu from json file"),
		OPT_END(),
	};
	struct argparse argparse;
	argparse_init(&argparse, options, usage, 0);
	argparse_describe(&argparse, "\nDisplays on-screen menu", NULL);
	argc = argparse_parse(&argparse, argc, (const char**)argv);
	if (filename == NULL) {
		argparse_usage(&argparse);
		return 1;
	}
	
	OSDMenu* mnu = osd_menu_new(filename);
	if (mnu != NULL) {
		g_signal_connect(G_OBJECT(mnu), "exit", (GCallback)&on_mnu_exit, NULL);
		g_signal_connect(G_OBJECT(mnu), "ready", (GCallback)&on_mnu_ready, NULL);
		osd_menu_connect(mnu);
		gtk_main();
		return 0;
	} else {
		return 1;
	}
}
