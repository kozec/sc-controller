#include "scc/utils/logging.h"
#include "scc/utils/traceback.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
#include "scc/osd/osd_menu.h"
#include "scc/tools.h"
#include "osd.h"
#include <gtk/gtk.h>

static int exit_code = 0;

static const char *const usage[] = {
	"scc-osd-menu -f <filename>",
	NULL,
};

static void on_mnu_exit(void* _mnu, int code) {
	exit_code = 0;
	gtk_main_quit();
}

static void on_mnu_ready(void* _mnu) {
	gtk_widget_show_all(GTK_WIDGET(_mnu));
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	gtk_init(&argc, &argv);
	
	OSDMenuSettings settings;
	if (!osd_menu_parse_args(argc, argv, usage, &settings))
		return 1;
	
	OSDMenu* mnu = osd_menu_new(settings.filename, &settings);
	if (mnu != NULL) {
		g_signal_connect(G_OBJECT(mnu), "exit", (GCallback)&on_mnu_exit, NULL);
		g_signal_connect(G_OBJECT(mnu), "ready", (GCallback)&on_mnu_ready, NULL);
		osd_menu_connect(mnu);
		gtk_main();
		gtk_widget_destroy(GTK_WIDGET(mnu));
		return exit_code;
	} else {
		return 1;
	}
}

