#include "scc/utils/logging.h"
#include "scc/utils/traceback.h"
#include "scc/utils/iterable.h"
#include "scc/utils/argparse.h"
#include "scc/utils/assert.h"
#include "scc/osd/osd_menu.h"
#include "scc/tools.h"
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
	
	OSDMenuSettings settings = { NULL, 1.0, NULL, PST_STICK, B_A, B_B };
	char* filename = NULL;
	char* control_with = NULL;
	char* confirm_with = NULL;
	char* cancel_with = NULL;
	struct argparse_option options[] = {
		OPT_HELP(),
		OPT_GROUP("Basic options"),
		OPT_STRING('f', "from-file", &filename, "load menu from json file"),
		OPT_STRING('t', "type", &settings.plugin_name, "menu type (plugin) to use. Available types: 'vmenu' (default), 'hmenu'"),
		OPT_STRING('c', "control-with", &control_with, "sets which pad or stick should be used to navigate menu. Defaults to STICK"),
		OPT_STRING(0, "confirm-with", &confirm_with, "button used to confirm choice. Defaults to A"),
		OPT_STRING(0, "cancel-with", &cancel_with, "button used to cancel menu. Defaults to B"),
		OPT_BOOLEAN('u', "use-cursor", &settings.use_cursor, "display and use cursor to navigate menu"),
		OPT_FLOAT(0, "size", &settings.icon_size, "icon size. Defaults to 1"),
		OPT_END(),
	};
	struct argparse argparse;
	argparse_init(&argparse, options, usage, 0);
	argparse_describe(&argparse, "\nDisplays on-screen menu", NULL);
	argc = argparse_parse(&argparse, argc, (const char**)argv);
	if (argc < 0)
		return (argc != -5);
	
	if (filename == NULL) {
		argparse_usage(&argparse);
		return 1;
	}
	if (settings.plugin_name == NULL)
		settings.plugin_name = "vmenu";
	if (control_with != NULL) {
		settings.control_with = scc_string_to_pst(control_with);
		if (strcmp(control_with, "DEFAULT") == 0) {
			settings.control_with = PST_STICK;
		} else if ((settings.control_with == 0)
					|| (settings.control_with == PST_LTRIGGER)
					|| (settings.control_with == PST_RTRIGGER)) {
			LERROR("Invalid value for '--control-with' option: '%s'", control_with);
			return 1;
		}
	}
	// TODO: Actual support for DEFAULT here
	if (confirm_with != NULL) {
		settings.confirm_with = scc_string_to_button(confirm_with);
		if (strcmp(confirm_with, "DEFAULT") == 0) {
			settings.confirm_with = B_A;
		} if (strcmp(confirm_with, "SAME") == 0) {
			if (settings.control_with == PST_LPAD)
				settings.confirm_with = B_LPADTOUCH;
			else if (settings.control_with == PST_RPAD)
				settings.confirm_with = B_RPADTOUCH;
		} else if (settings.confirm_with == 0) {
			LERROR("Invalid value for '--confirm-with' option: '%s'", confirm_with);
			return 1;
		}
	}
	if (cancel_with != NULL) {
		settings.cancel_with = scc_string_to_button(cancel_with);
		if (strcmp(confirm_with, "DEFAULT") == 0) {
			settings.confirm_with = B_B;
		} else if (settings.cancel_with == 0) {
			LERROR("Invalid value for '--cancel-with' option: '%s'", control_with);
			return 1;
		}
	}
	
	OSDMenu* mnu = osd_menu_new(filename, &settings);
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
