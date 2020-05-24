/**
 * SC Controller - Input Tester
 *
 * Small tool used to test drivers and called from GUI when generating bindings.
 */
#define LOG_TAG "InputTest"
#include "scc/utils/strbuilder.h"
#include "scc/utils/traceback.h"
#include "scc/utils/iterable.h"
#include "scc/utils/argparse.h"
#include "scc/utils/logging.h"
#include "scc/utils/list.h"
#include "scc/utils/math.h"
#include "scc/input_device.h"
#include "scc/tools.h"
#include "daemon.h"
#include <sys/stat.h>
#include <unistd.h>
#ifndef _WIN32
#include <sys/types.h>
#include <signal.h>
#else
#include "scc/client.h"
#endif
#include <errno.h>
#include <stdio.h>

static const char *const usage[] = {
	"scc-input-test [-t driver] device",
	"scc-input-test --list [--all]",
	"scc-input-test -h",
	"",
	"Data on output, where applicable, is tab (\\t) separated",
	NULL,
};

static LIST_TYPE(sccd_mainloop_cb) mainloop_callbacks;
static Controller* controller = NULL;
static char* device_id = NULL;
static bool running = false;
static bool list_all = false;
static char* argv0;
#ifndef _WIN32
static size_t max_argv0_size = 0;
#endif


static bool controller_add(Controller* c) {
	if (controller != NULL)
		return false;
	controller = c;
	return true;
}

static bool add_mainloop(sccd_mainloop_cb cb) {
	return list_add(mainloop_callbacks, cb);
}

static void controller_remove(Controller* c) {
}

static void remove_mainloop(sccd_mainloop_cb cb) {
	// list_remove(mainloop_callbacks, cb);
}

Controller* sccd_get_controller_by_id(const char* id) {
	return NULL;
}

intptr_t sccd_error_add(const char* message, bool fatal) {
	return 1;
}

void sccd_error_remove(intptr_t id) { }

static void schedule_cb(void* cb, void* userdata) {
	((sccd_scheduler_cb)(cb))(userdata);
}

static TaskID schedule(uint32_t timeout, sccd_scheduler_cb cb, void* userdata) {
	return sccd_scheduler_schedule(timeout, &schedule_cb, (void*)cb, userdata);
}

static bool sccd_hidapi_enabled() {
#if USE_HIDAPI
	return true;
#else
	return false;
#endif
}

void* sccd_x11_get_display() {
	return NULL;
}


static Daemon _daemon = {
	.controller_add				= controller_add,
	.controller_remove			= controller_remove,
	.error_add					= sccd_error_add,
	.error_remove				= sccd_error_remove,
	.mainloop_cb_add			= add_mainloop,
	.mainloop_cb_remove			= remove_mainloop,
	.schedule					= schedule,
	.cancel						= sccd_scheduler_cancel,
	.poller_cb_add				= sccd_poller_add,
	.hotplug_cb_add				= sccd_register_hotplug_cb,
	.get_controller_by_id		= sccd_get_controller_by_id,
	.get_x_display				= sccd_x11_get_display,
	.get_config_path			= scc_get_config_path,
	.get_hidapi_enabled			= sccd_hidapi_enabled,
};

Daemon* get_daemon() {
	return &_daemon;
}

static void sigint_handler(int sig) {
	INFO("^C caught");
	running = false;
}

static void dev_null_logging_handler(const char* tag, const char* filename, int level, const char* message) {
	// Maybe really open /dev/null to write to it? :)
}

inline static const char* or_questionmarks(char* a) {
	if (a == NULL)
		return "????";
	return a;
}

static void controller_test_event(Controller* c, TestModeEvent event, uint32_t code, int64_t value) {
	if ((event == TME_BUTTON) && value) {
		printf("button_press\t%u\n", code);
	} else if (event == TME_BUTTON) {
		printf("button_release\t%u\n", code);
	} else if (event == TME_AXIS) {
		printf("axis_update\t%u\t%li\n", code, value);
	}
	fflush(stdout);
}

static void controller_available_list(const char* driver_name, uint8_t confidence,
			const InputDeviceData* idev) {
	static char buffer[256];
	const char* path = NULL;
	char* nice_path = NULL;
	char* name = NULL;
	if (!list_all && (confidence < 5))
		return;
#ifdef __linux__
	if (idev->subsystem == EVDEV) {
		char* a = idev->get_prop(idev, "device/modalias");
		if (a == NULL) return;
		if (strstr(a, "input") != a) {
			free(a);
			return;
		}
		free(a);
		path = strrchr(idev->path, '/');
		if (path != NULL) {
			nice_path = strbuilder_fmt("/dev/input/%s", path + 1);
			path = nice_path;
		}
	} else {
		path = idev->path;
		path =  strstr(idev->path, "usb");
	}
	if (path == NULL)
		path = idev->path;
	char* vendor = idev->get_prop(idev, "vendor_id");
	if ((vendor != NULL) && (0 == strcmp(vendor, "0000"))) {
		// Internal, definitelly not gamepad related stuff. Skip it
		free(vendor);
		return;
	}
	char* product = idev->get_prop(idev, "product_id");
	char icon = (confidence > 5) ? 'c' : '?';
	name = idev->get_name(idev);
	snprintf(buffer, 256, "%s:%s", or_questionmarks(vendor), or_questionmarks(product));
	printf("%c %-15s\t%-15s\t%-23s\t%s\n", icon, buffer, driver_name, path, or_questionmarks(name));
	free(nice_path);
	free(product);
	free(vendor);
	free(name);
#endif
}

static void controller_available_test(const char* driver_name, uint8_t confidence,
			const InputDeviceData* idev) {
	HotplugFilter filter;
	if (strchr(device_id, '/') != NULL) {
		// device_id is actually path
		filter.type = SCCD_HOTPLUG_FILTER_PATH;
		filter.path = device_id;
	} else {
#ifdef __linux__
		filter.type = SCCD_HOTPLUG_FILTER_VIDPID;
		filter.vidpid = device_id;
#endif
	}
	if (sccd_device_monitor_test_filter(&_daemon, idev, &filter)) {
		Driver* drv = sccd_drivers_get_by_name(driver_name);
		if ((drv == NULL) || (drv->test_device == NULL))
			return;
		drv->test_device(drv, &_daemon, idev, controller_test_event);
	}
}


int main(int argc, char** argv) {
	argv0 = argv[0];
	traceback_set_argv0(argv[0]);
	bool list = false;
#ifndef _WIN32
	for (int i=0; i<argc; i++)
		max_argv0_size += strlen(argv[i]) + 1;
#endif
	
	struct argparse_option options[] = {
		OPT_HELP(),
		OPT_BOOLEAN(0, "list", &list,		"list available controllers", NULL),
		// TODO: This option. Or rather, don't automatically do that
		OPT_BOOLEAN(0, "all", &list_all,	"list not only controllers, but all input devices", NULL),
		OPT_END(),
	};
	struct argparse argparse;
	argparse_init(&argparse, options, usage, 0);
	argparse_describe(&argparse, "\nSC-Controller Input Tester", NULL);
	argc = argparse_parse(&argparse, argc, (const char**)argv);
	if (argc < 0)
		return 1;
	if (!list && (argc < 1)) {
		argparse_usage(&argparse);
		return 1;
	} else {
		device_id = argv[0];
	}
	
	mainloop_callbacks = list_new(sccd_mainloop_cb, 0);
	sccd_scheduler_init();
	sccd_poller_init();
#ifdef USE_LIBUSB
	sccd_input_libusb_init(&_daemon);
#endif
	sccd_device_monitor_init(&_daemon);
	logging_handler handler = logging_set_handler(dev_null_logging_handler);
	sccd_drivers_init(&_daemon, DIMODE_LIST_DEVICES_ONLY);
	logging_set_handler(handler);
	
	if (list) {
		printf("  %-15s\t%-15s\t%-23s\t%s\n", "Device", "Driver", "Path", "Description");
		// Disable logging while drivers are initialized
		sccd_drivers_list_devices(&_daemon, controller_available_list);
		sccd_device_monitor_rescan(&_daemon);
	} else if (device_id != NULL) {
		sccd_drivers_list_devices(&_daemon, controller_available_test);
		sccd_device_monitor_rescan(&_daemon);
		
		if (controller == NULL) {
			LERROR("No such device");
			return 1;
		} else {
			printf("Ready. Press some buttons...\n");
			fflush(stdout);
		}
		
		ListIterator iter = iter_get(mainloop_callbacks);
		running = true;
		signal(SIGTERM, sigint_handler);
		signal(SIGINT, sigint_handler);
		while (running) {
			monotime_t start = mono_time_ms();
			FOREACH(sccd_mainloop_cb, cb, iter)
				cb(&_daemon);
			// list_foreach(mappers, (list_foreach_cb)sccd_mapper_flush);
			iter_reset(iter);
			monotime_t end = mono_time_ms();
			if (end - start < 10)
				usleep((10 - (end - start)) * 1000);
		}
		if (controller != NULL) {
			controller->deallocate(controller);
		}
	}
	
	return 0;
}

