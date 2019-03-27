/**
 * SC Controller - User Interface - main module
 *
 * This is GUI v1.5 - v1 being .py file and potential v2 being written completly
 * in something native.
 *
 * v1.5 is loader that makes sure that correct python version loads correct
 * python file.
 */
#define LOG_TAG "GUI"
#include "Python.h"
#include "scc/utils/traceback.h"
#include "scc/utils/logging.h"
#include "scc/tools.h"
#include "../daemon/version.h"

#define LIB_PYTHON_PATH ":/usr/lib/python2.7" \
						":/usr/lib/python2.7/plat-linux2" \
						":/usr/lib/python2.7/lib-dynload" \
						":/usr/lib/python2.7/site-packages"

int main(int argc, char** argv) {
	INFO("Starting SC Controller GUI v%s...", DAEMON_VERSION);
	// Just btw, GUI version and DAEMON_VERSION should match. GUI will
	// try to get rid of old daemon automatically
	traceback_set_argv0(argv[0]);
	
	DEBUG("Initializing python...");
	Py_Initialize();
	char* sys_path = malloc(PATH_MAX * 2);
	snprintf(sys_path, PATH_MAX * 2,
				"%s" LIB_PYTHON_PATH, scc_get_python_src_path());
	PySys_SetPath(sys_path);
	
	PyObject* gui = PyImport_ImportModule("gui_loader");
	if (PyErr_Occurred()) {
		LERROR("Failed to initialize gui_loader.py:");
		PyErr_PrintEx(0);
		return 1;
	}
	if (gui == NULL) {
		LERROR("Failed to load gui_loader.py! Exiting...");
		return 1;
	}
	Py_DECREF(gui);
	
	return 0;
}

