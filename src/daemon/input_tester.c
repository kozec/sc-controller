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
	"scc-input-test device",
	"scc-input-test --gamecontrollerdb-id device",
	// "scc-input-test --list [--all]",
	"scc-input-test --list",
	"scc-input-test --first",
	"scc-input-test -h",
	"",
	"Data on output, where applicable, is tab (\\t) separated",
	NULL,
};

/**
 * Formatting of 'Device Driver Path Description' table.
 * As guid used on Windows is much, much longer than IDs used elsewhere,
 * different column length is needed.
 */
#ifndef _WIN32
#define TABLE_COLUMNS "%c %-15s\t%-15s\t%-23s\t%s\n"
#else
#define TABLE_COLUMNS "%c %-40s\t%-15s\t%-48s\t%s\n"
#endif

#define BUTTON_AXIS_MAX		256
static LIST_TYPE(sccd_mainloop_cb) mainloop_callbacks;
static Controller* controller = NULL;
static char* device_id = NULL;
static bool running = false;
static bool opt_gamecontrollerdb_id = false;
static bool opt_list_all = false;
static bool opt_first = false;
static bool opt_list = false;
static char* argv0;

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


#ifndef _WIN32
static void sigint_handler(int sig) {
	INFO("^C caught");
	running = false;
}
#endif

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
		printf("axis_update\t%u\t%lli\n", code, value);
	}
	fflush(stdout);
}

static void controller_available_list(const char* driver_name, uint8_t confidence,
			const InputDeviceData* idev) {
	const char* path = NULL;
	char* nice_path = NULL;
	char* unique_id = NULL;
	char* name = NULL;
	if (!opt_list_all && (confidence < 5))
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
#endif
	if (path == NULL)
		path = idev->path;
#ifndef _WIN32
	char* vendor = idev->get_prop(idev, "vendor_id");
	if ((vendor != NULL) && (0 == strcmp(vendor, "0000"))) {
		// Internal, definitelly not gamepad related stuff. Skip it
		free(vendor);
		return;
	}
	free(vendor);
#endif
	unique_id = idev->get_prop(idev, "unique_id");
	char icon = (confidence > 5) ? 'c' : '?';
	name = idev->get_name(idev);
	if (unique_id != NULL) {
		printf(TABLE_COLUMNS,
				icon, unique_id, driver_name, path, or_questionmarks(name));
	}
	free(unique_id);
	free(nice_path);
	free(name);
}

static bool controller_add(Controller* c) {
	if (controller != NULL)
		return false;
	controller = c;
	return true;
}

/**
 * Parses string as integer and swaps higher bytes with lower.
 * **deallocates** 'number'.
 * Returns 0 if 'number' is NULL.
 */
static int wordswap(char* number) {
	int i = 0;
	if (number != NULL) {
		i = strtol(number, NULL, 16);
		free(number);
	}
	return ((i & 0xFF) << 8) | ((i & 0xFF00) >> 8);
}

static void print_gamecontrollerdb_id(const InputDeviceData* idev) {
	// Note: This is as platform-dependent as it can be
	printf("%.4x%.8x%.8x%.8x0000\n",
#ifdef _WIN32
			0x0300,		// Everything is 0x03 on Windows
#else
			0x0300,		// TODO: BT support. 0x03 stands for USB
#endif
			wordswap(idev->get_prop(idev, "vendor_id")),
			wordswap(idev->get_prop(idev, "product_id")),
			wordswap(idev->get_prop(idev, "version_id"))
	);
}

static void controller_available_test(const char* driver_name, uint8_t confidence,
			const InputDeviceData* idev) {
	HotplugFilter filter;
	Daemon* daemon = get_daemon();
	if (strchr(device_id, '/') != NULL) {
		// device_id is actually path
		filter.type = SCCD_HOTPLUG_FILTER_PATH;
		filter.path = device_id;
#ifdef __linux__
	} else if (strchr(device_id, ':') != NULL) {
		filter.type = SCCD_HOTPLUG_FILTER_VIDPID;
		filter.vidpid = device_id;
#endif
	} else {
		filter.type = SCCD_HOTPLUG_FILTER_UNIQUE_ID;
		filter.id = device_id;
	}
	if (opt_first || sccd_device_monitor_test_filter(daemon, idev, &filter)) {
		if (opt_gamecontrollerdb_id)
			return print_gamecontrollerdb_id(idev);
		Driver* drv = sccd_drivers_get_by_name(driver_name);
		if ((drv == NULL) || (drv->input_test == NULL)
					|| (drv->input_test->test_device == NULL))
			return;
		drv->input_test->test_device(drv, daemon, idev, controller_test_event);
		if (controller != NULL) {
			// Controller was just added
			if (drv->input_test->get_device_capabilities != NULL) {
				uint32_t buttons[BUTTON_AXIS_MAX];
				uint32_t axes[BUTTON_AXIS_MAX];
				InputDeviceCapabilities capabilities = {
					.max_button_count = BUTTON_AXIS_MAX,
					.max_axis_count = BUTTON_AXIS_MAX,
					.buttons = buttons,
					.axes = axes
				};
				drv->input_test->get_device_capabilities(drv, daemon, idev, &capabilities);
				if (capabilities.button_count > 0) {
					printf("buttons:");
					for (size_t i=0; i<capabilities.button_count; i++)
						printf(" %i", capabilities.buttons[i]);
					printf("\n");
				}
				if (capabilities.axis_count > 0) {
					printf("axes:");
					for (size_t i=0; i<capabilities.axis_count; i++)
						printf(" %i", capabilities.axes[i]);
					printf("\n");
				}
			}
			// Should we be doing "--first" option, no more controllers can be first
			opt_first = false;
		}
	}
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


int main(int argc, char** argv) {
	argv0 = argv[0];
	traceback_set_argv0(argv[0]);
	
	struct argparse_option options[] = {
		OPT_HELP(),
		OPT_BOOLEAN(0, "list", &opt_list,
				"list available controllers", NULL),
		OPT_BOOLEAN(0, "gamecontrollerdb-id", &opt_gamecontrollerdb_id,
				"for given device, prints ID compatible with SDL_GameControllerDB", NULL),
		// OPT_BOOLEAN(0, "all", &opt_list_all,
		// 		"list not only controllers, but all input devices", NULL),
		OPT_BOOLEAN(0, "first", &opt_first,
				"start testing first available controller", NULL),
		OPT_END(),
	};
	struct argparse argparse;
	argparse_init(&argparse, options, usage, 0);
	argparse_describe(&argparse, "\nSC-Controller Input Tester", NULL);
	argc = argparse_parse(&argparse, argc, (const char**)argv);
	if (argc < 0)
		return 1;
	if (!opt_list && !opt_first && (argc < 1)) {
#ifdef _WIN32
		// Windows-only: If no argument is specified, list all devices
		opt_list = 1;
#else
		// Anywhere else: If no argument is specified, print help & exit
		argparse_usage(&argparse);
		return 1;
#endif
	} else if (opt_first) {
		device_id = "first";
	} else {
		device_id = argv[0];
	}
	
	mainloop_callbacks = list_new(sccd_mainloop_cb, 0);
	sccd_scheduler_init();
#ifdef _WIN32
	logging_handler handler = logging_set_handler(dev_null_logging_handler);
	sccd_input_dinput_init();
#else
	sccd_poller_init();
#endif
#ifdef USE_LIBUSB
	sccd_input_libusb_init(&_daemon);
#endif
	sccd_device_monitor_init(&_daemon);
#ifndef _WIN32
	logging_handler handler = logging_set_handler(dev_null_logging_handler);
#endif
	sccd_drivers_init(&_daemon, DIMODE_LIST_DEVICES_ONLY);
	logging_set_handler(handler);
	
	if (opt_list) {
		printf(TABLE_COLUMNS, ' ', "Device", "Driver", "Path", "Description");
		// Disable logging while drivers are initialized
		sccd_drivers_list_devices(&_daemon, controller_available_list);
		sccd_device_monitor_rescan(&_daemon);
	} else if (device_id != NULL) {
		sccd_drivers_list_devices(&_daemon, controller_available_test);
		sccd_device_monitor_rescan(&_daemon);
		
		if (opt_gamecontrollerdb_id) {
			return 0;
		} else if (controller == NULL) {
			LERROR("No such device");
			return 1;
		} else {
			printf("Ready. Press some buttons...\n");
			fflush(stdout);
		}
		
		ListIterator iter = iter_get(mainloop_callbacks);
		running = true;
#ifndef _WIN32
		signal(SIGTERM, sigint_handler);
		signal(SIGINT, sigint_handler);
#endif
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

