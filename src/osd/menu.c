#include "scc/utils/traceback.h"
#include "scc/utils/iterable.h"
#include "scc/utils/argparse.h"
#include "scc/utils/assert.h"
#include "scc/osd/osd_menu.h"
#include <gtk/gtk.h>

static const char *const usage[] = {
	"scc-ost-menu -f <filename>",
	NULL,
};

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
		gtk_widget_show_all(GTK_WIDGET(mnu));
		gtk_main();
		return 0;
	} else {
		return 1;
	}
}
