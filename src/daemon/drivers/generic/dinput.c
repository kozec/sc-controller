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

static void input_interrupt_cb(Daemon* d, InputDevice* dev, uint8_t endpoint, const uint8_t* data, void* _c) {
	DInputController* di = (DInputController*)_c;
	if (memcmp(&di->old_state, data, sizeof(DIJOYSTATE2)) == 0)
		// No change in state
		return;
	memcpy(&di->old_state, data, sizeof(DIJOYSTATE2));
	DIJOYSTATE2* state = (DIJOYSTATE2*)data;
	LONG* axes = (LONG*)state;					// 8 axes followed by POV hat
	
	memset(&di->gc.input, 0, sizeof(ControllerInput));
	for(intptr_t i=0; i<=di->gc.button_max; i++) {
		any_t val;
		if (intmap_get(di->gc.button_map, i, &val) != MAP_OK)
			continue;
		if (state->rgbButtons[i])
			di->gc.input.buttons |= (SCButton)val;
		else
			di->gc.input.buttons &= ~(SCButton)val;
	}
	for(intptr_t i=0; i<8; i++) {
		AxisData* ad;
		if (intmap_get(di->gc.axis_map, i, (any_t)&ad) != MAP_OK)
			continue;
		apply_axis(ad, (double)axes[i], &di->gc.input);
	}
	// TODO: DPad
	// TODO: Allow to disable PADPRESS_EMULATION
	/*
	if ((di->gc.input.buttons & ~old_buttons & (B_LPADTOUCH | B_RPADTOUCH)) != 0) {
		if (di->gc.padpressemu_task != 0)
			d->cancel(di->gc.padpressemu_task);
		di->gc.padpressemu_task = d->schedule(PADPRESS_EMULATION_TIMEOUT,
										&gc_cancel_padpress_emulation, &di->gc);
	}*/
	/*
	LOG(">>> %i %i %i %i",
			state->rgdwPOV[0],
			state->rgdwPOV[1],
			state->rgdwPOV[2],
			state->rgdwPOV[3]);
	*/
	if (di->gc.mapper != NULL)
		di->gc.mapper->input(di->gc.mapper, &di->gc.input);
}


static inline char* dinput_idev_to_config_key(const InputDeviceData* idev) {
	return idev->get_prop(idev, "guidInstance");
}


static void hotplug_cb(Daemon* d, const InputDeviceData* idev) {
	char error[1024];
	char* ckey = dinput_idev_to_config_key(idev);
	Config* cfg = config_load();
	if ((cfg == NULL) || (ckey == NULL)) {
		RC_REL(cfg);
		free(ckey);
		return;
	}
	Config* ccfg = config_get_controller_config(cfg, ckey, NULL);
	RC_REL(cfg);
	if (ccfg == NULL) {
		WARN("%s: %s", ckey, error);
		free(ckey);
		return;
	}
	
	DInputController* di = malloc(sizeof(DInputController));
	if (di != NULL) memset(di, 0, sizeof(DInputController));
	if ((di == NULL) || !gc_alloc(d, &di->gc)) {
		// OOM
		RC_REL(ccfg);
		free(ckey);
		free(di);
	}
	
	snprintf(di->gc.desc, MAX_DESC_LEN, "<dinput %s>", ckey);
	di->gc.desc[MAX_DESC_LEN - 1] = 0;
	if (di->gc.desc[MAX_DESC_LEN - 2] != 0)
		di->gc.desc[MAX_DESC_LEN - 2] = '>';
	free(ckey);
	
	if (!gc_load_mappings(&di->gc, ccfg)) {
		dinput_dealloc(&di->controller);
		RC_REL(ccfg);
		return;
	}
	
	StrBuilder* sb = strbuilder_new();
	char* uniq = idev->get_prop(idev, "guidInstance");
	if (uniq != NULL) {
		uLong crc = crc32(0, (const Bytef*)uniq, strlen(uniq));
		strbuilder_addf(sb, "%x", crc);
		free(uniq);
		strbuilder_upper(sb);
		strbuilder_insert(sb, 0, "dinput");
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
	
	if (!d->controller_add(&di->controller)) {
		LERROR("Failed to add new controller");
		dinput_dealloc(&di->controller);
	}
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

static void list_devices_hotplug_cb(Daemon* d, const InputDeviceData* idev) {
	controller_available("dinput", 9, idev);
}

static void driver_list_devices(Driver* drv, Daemon* d,
										const controller_available_cb ca) {
	controller_available = ca;
	d->hotplug_cb_add(DINPUT, list_devices_hotplug_cb, NULL);
}


static Driver driver = {
	.unload = NULL,
	.start = driver_start,
	.input_test = &((InputTestMethods) {
		.list_devices = driver_list_devices,
		// .test_device = driver_test_device,
		// .get_device_capabilities = driver_get_device_capabilities,
	})
};

Driver* scc_driver_init(Daemon* daemon) {
	return &driver;
}

