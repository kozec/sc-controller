/**
 * Generic SC-Controller driver - hidapi
 *
 * Implementation that uses hidapi on Windows
 */
#include "generic.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/input_device.h"
#include "scc/input_test.h"
#include "scc/driver.h"
#include "scc/config.h"
#include "scc/mapper.h"
#include <windows.h>
#include <winbase.h>
#include <dinput.h>
#include <zlib.h>

static controller_available_cb controller_available = NULL;
static controller_test_cb controller_test = NULL;
#define DI_MAX_AXES			8
#define DI_MAX_HATS			2
#define DI_BUTTONS_OFFSET	64
#define DI_BUTTON_COUNT		128

typedef struct DInputController {
	Controller				controller;
	GenericController		gc;
	DIJOYSTATE2				old_state;
	InputDevice*			dev;
} DInputController;


static const char* dinput_get_type(Controller* c) {
	return "dinput";
}

static void dinput_dealloc(Controller* c) {
	DInputController* di = container_of(c, DInputController, controller);
	gc_dealloc(&di->gc);
	if (di->dev != NULL)
		di->dev->close(di->dev);
	free(di);
}

/**
 * Converts pov hat position to two axes.
 * 'pov' position is indicated in hundredths of a degree clockwise from
 * north (away from the user). The center position is normally reported as -1,
 * unless it's reported as 0xFFFF
 */
static void pow_to_axis(DWORD pov, LONG* x, LONG* y) {
	// TODO: Maybe do actual math here? All pads I have reports POV only in 45
	// TODO: degrees steps. Is there actual device that would excuse calling
	// TODO: sin / cos all the time?
	if ((pov == 0xFFFF) || (pov > 36000)) {
		// Centered
		*x = *y = 0;
	} else if (pov < 4500) {
		*x = 0; *y = -1;
	} else if (pov < 9000) {
		*x = 1; *y = -1;
	} else if (pov < 13500) {
		*x = 1; *y = 0;
	} else if (pov < 18000) {
		*x = 1; *y = 1;
	} else if (pov < 22500) {
		*x = 0; *y = 1;
	} else if (pov < 27000) {
		*x = -1; *y = 1;
	} else if (pov < 31500) {
		*x = -1; *y = 0;
	} else {
		*x = -1; *y = -1;
	}
}

static void input_interrupt_cb(Daemon* d, InputDevice* dev, uint8_t endpoint, const uint8_t* data, void* _c) {
	DInputController* di = (DInputController*)_c;
	if (memcmp(&di->old_state, data, sizeof(DIJOYSTATE2)) == 0)
		// No change in state
		return;
	DIJOYSTATE2* state = (DIJOYSTATE2*)data;
	LONG* axes = (LONG*)state;					// 8 axes followed by POV hat
	
	memset(&di->gc.input, 0, sizeof(ControllerInput));
	// Buttons
	for(intptr_t i = 0; i <= di->gc.button_max; i++) {
		if (state->rgbButtons[i] != di->old_state.rgbButtons[i]) {
			if (controller_test != NULL)
				controller_test(&di->controller, TME_BUTTON,
						DI_BUTTONS_OFFSET + i, state->rgbButtons[i]);
			else {
				apply_button(d, &di->gc,
						DI_BUTTONS_OFFSET + i, state->rgbButtons[i]);
				apply_axis(&di->gc, DI_BUTTONS_OFFSET + i,
						(double)(state->rgbButtons[i]
								? STICK_PAD_MAX : STICK_PAD_MIN));
			}
		}
	}
	// Axes
	for(intptr_t i = 0; i < DI_MAX_AXES; i++) {
		if (axes[i] != ((LONG*)&di->old_state)[i]) {
			if (controller_test != NULL)
				controller_test(&di->controller, TME_AXIS, i, axes[i]);
			else
				apply_axis(&di->gc, i, (double)axes[i]);
		}
	}
	// Hats
	for(intptr_t i = 0; i < DI_MAX_HATS * 2; i++) {
		if (state->rgdwPOV[i] != di->old_state.rgdwPOV[i]) {
			LONG x, y;
			pow_to_axis(state->rgdwPOV[i], &x, &y);
			if (controller_test != NULL) {
				controller_test(&di->controller, TME_AXIS,
						DI_MAX_AXES + 0 + i * 2, x);
				controller_test(&di->controller, TME_AXIS,
						DI_MAX_AXES + 1 + i * 2, y);
			} else {
				apply_axis(&di->gc, DI_MAX_AXES + 0 + i * 2, (double)x);
				apply_axis(&di->gc, DI_MAX_AXES + 1 + i * 2, (double)y);
			}
		}
	}
	// TODO: Emulate PADPRESS when POV is non-zero
	// TODO: Allow to disable that
	if (di->gc.mapper != NULL)
		di->gc.mapper->input(di->gc.mapper, &di->gc.input);
	
	memcpy(&di->old_state, data, sizeof(DIJOYSTATE2));
}

static inline char* dinput_idev_to_config_key(const InputDeviceData* idev) {
	char* ckey = malloc(1024);
	snprintf(ckey, 1023, "dinput-%s", idev->get_prop(idev, "guidInstance"));
	return ckey;
}

static void open_device(Daemon* d, const InputDeviceData* idev, Config* ccfg, const char* ckey) {
	DInputController* di = malloc(sizeof(DInputController));
	if (di != NULL) memset(di, 0, sizeof(DInputController));
	if ((di == NULL) || !gc_alloc(d, &di->gc)) {
		// OOM
		free(di);
	}
	
	snprintf(di->gc.desc, MAX_DESC_LEN, "<dinput %s>", ckey);
	di->gc.desc[MAX_DESC_LEN - 1] = 0;
	if (di->gc.desc[MAX_DESC_LEN - 2] != 0)
		di->gc.desc[MAX_DESC_LEN - 2] = '>';
	
	if (!gc_load_mappings(&di->gc, ccfg)) {
		dinput_dealloc(&di->controller);
		return;
	}
	
	StrBuilder* sb = strbuilder_new();
	char* uniq = idev->get_prop(idev, "guidInstance");
	if (uniq != NULL) {
		strbuilder_add(sb, "dinput-");
		strbuilder_add(sb, uniq);
		free(uniq);
	}
	if ((uniq == NULL) || strbuilder_failed(sb)) {
		dinput_dealloc(&di->controller);
		LERROR("Failed to configure controller: Out of memory");
		return;
	}
	gc_make_id(strbuilder_get_value(sb), &di->gc);
	
	InputDevice* dev = idev->open(idev);
	if (dev == NULL) {
		LERROR("Failed open '%s'", idev->path);
		dinput_dealloc(&di->controller);
		return;
	}
	if (!dev->interupt_read_loop(dev, 0, sizeof(DIJOYSTATE2), input_interrupt_cb, di)) {
		LERROR("Failed to configure controller");
		dev->close(dev);
		dinput_dealloc(&di->controller);
		return;
	}
	
	di->controller.flags = CF_HAS_DPAD | CF_NO_GRIPS | CF_HAS_RSTICK | CF_SEPARATE_STICK;
	di->controller.deallocate = dinput_dealloc;
	di->controller.get_id = gc_get_id;
	di->controller.get_type = dinput_get_type;
	di->controller.get_description = gc_get_description;
	di->controller.set_mapper = gc_set_mapper;
	di->controller.turnoff = gc_turnoff;
	di->controller.set_gyro_enabled = NULL;
	di->controller.get_gyro_enabled = NULL;
	di->controller.flush = NULL;
	di->dev = dev;
	
	if (controller_test != NULL)
		di->gc.button_max = DI_BUTTON_COUNT;
	
	if (!d->controller_add(&di->controller)) {
		LERROR("Failed to add new controller");
		dinput_dealloc(&di->controller);
	}
}

static bool hotplug_cb(Daemon* d, const InputDeviceData* idev) {
	char error[1024];
	char* ckey = dinput_idev_to_config_key(idev);
	Config* cfg = config_load();
	if ((cfg == NULL) || (ckey == NULL)) {
		RC_REL(cfg);
		free(ckey);
		return false;
	}
	Config* ccfg = config_get_controller_config(cfg, ckey, NULL);
	RC_REL(cfg);
	if (ccfg == NULL) {
		free(ckey);
		return false;
	}
	
	open_device(d, idev, ccfg, ckey);
	RC_REL(ccfg);
	free(ckey);
	return true;
}

static bool driver_start(Driver* drv, Daemon* daemon) {
	// TODO: Don't register everything, list known devices and register handlers
	// TODO: only for those instead
	if (!daemon->hotplug_cb_add(DINPUT, hotplug_cb, NULL)) {
		LERROR("Failed to register hotplug callback");
		return false;
	}
	return true;
}

static bool list_devices_hotplug_cb(Daemon* d, const InputDeviceData* idev) {
	controller_available("dinput", 9, idev);
	return true;
}

static void driver_list_devices(Driver* drv, Daemon* d,
										const controller_available_cb ca) {
	controller_available = ca;
	d->hotplug_cb_add(DINPUT, list_devices_hotplug_cb, NULL);
}

static void driver_get_device_capabilities(Driver* drv, Daemon* daemon,
									const InputDeviceData* idev,
									InputDeviceCapabilities* capabilities) {
	capabilities->button_count = min(capabilities->max_button_count, DI_BUTTON_COUNT);
	capabilities->axis_count = DI_MAX_AXES + DI_MAX_HATS * 2;
	// ^^ 8 supported by DINPUT + 2*4 POV hats
	for (int i = 0; i < capabilities->button_count; i++)
		capabilities->buttons[i] = DI_BUTTONS_OFFSET + i;
	for (int i = 0; i < capabilities->axis_count; i++)
		capabilities->axes[i] = i;
}

static void driver_test_device(Driver* drv, Daemon* daemon,
			const InputDeviceData* idata,  const controller_test_cb test_cb) {
	controller_test = test_cb;
	open_device(daemon, idata, NULL, "test");
}


static Driver driver = {
	.unload = NULL,
	.start = driver_start,
	.input_test = &((InputTestMethods) {
		.list_devices = driver_list_devices,
		.test_device = driver_test_device,
		.get_device_capabilities = driver_get_device_capabilities,
	})
};

Driver* scc_driver_init(Daemon* daemon) {
	return &driver;
}

