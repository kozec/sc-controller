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
#include "scc/utils/strbuilder.h"
#include "scc/utils/traceback.h"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/tools.h"
#include "../daemon/version.h"

#define LIB_PYTHON_PATH ":/usr/lib/python2.7" \
						":/usr/lib/python2.7/plat-linux2" \
						":/usr/lib/python2.7/lib-dynload" \
						":/usr/lib/python2.7/site-packages"

#ifdef _WIN32
#ifdef FORCE_CONSOLE
int main(int argc, char** argv) {
	INFO("Starting SC Controller GUI (forced console) v%s...", DAEMON_VERSION);
#else	// FORCE_CONSOLE
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, LPSTR lpCmdLine, int nCmdShow) {
	FreeConsole();
#endif	// FORCE_CONSOLE
	_putenv("PYTHONIOENCODING=UTF-8");
	char* new_path = NULL;
	if (getenv("PATH") == NULL)
		new_path = strbuilder_fmt("PATH=%s", scc_get_exe_path());
	else
		new_path = strbuilder_fmt("PATH=%s;%s", scc_get_exe_path(), getenv("PATH"));
	ASSERT(new_path != NULL);
	_putenv(new_path);
	free(new_path);
#else	// _WIN32
int main(int argc, char** argv) {
	INFO("Starting SC Controller GUI v%s...", DAEMON_VERSION);
	// Just btw, GUI version and DAEMON_VERSION should match. GUI will
	// try to get rid of old daemon automatically
	traceback_set_argv0(argv[0]);
#endif	// _WIN32
	
	DEBUG("Initializing python...");
	StrBuilder* sys_path = strbuilder_new();
	strbuilder_add(sys_path, scc_get_python_src_path());
#ifdef _WIN32
	Py_SetProgramName("sc-controller.exe");
	
	// When running from release, this directory will exists and in so it will
	// be part of our PYTHONPATH.
	char* test = strbuilder_fmt("%s\\..\\lib\\python2.7", scc_get_python_src_path());
	ASSERT(test != NULL);
	if (access(test, F_OK) == 0) {
		free(test);
		char* root = strbuilder_fmt("%s\\..", scc_get_python_src_path());
		ASSERT(root != NULL);
		char* python_home = scc_realpath(root, NULL);
		ASSERT(python_home != NULL);
		free(root);
		DDEBUG("Python home: %s", python_home);
		Py_SetPythonHome((char*)python_home);
		Py_InitializeEx(0);
		strbuilder_addf(sys_path, ";%s\\python\\scc\\lib", python_home);
		strbuilder_addf(sys_path, ";%s\\lib\\python2.7", python_home);
		strbuilder_addf(sys_path, ";%s\\lib\\python2.7\\lib-dynload", python_home);
		strbuilder_addf(sys_path, ";%s\\lib\\python2.7\\site-packages", python_home);
	} else {
		Py_SetPythonHome("C:/msys32/mingw32/");
		Py_InitializeEx(0);
		strbuilder_add(sys_path, ";C:/msys32/mingw32/lib/python2.7");
		strbuilder_add(sys_path, ";C:/msys32/mingw32/lib/python2.7/lib-dynload");
		strbuilder_add(sys_path, ";C:/msys32/mingw32/lib/python2.7/site-packages");
	}
	DDEBUG("Python path: %s", strbuilder_get_value(sys_path));
#else
	Py_Initialize();
	strbuilder_add(sys_path, LIB_PYTHON_PATH);
#endif
	ASSERT(!strbuilder_failed(sys_path));
	PySys_SetPath((char*)strbuilder_get_value(sys_path));
	
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
	
	strbuilder_free(sys_path);
	DEBUG("Python code finished.");
	
	return 0;
}

