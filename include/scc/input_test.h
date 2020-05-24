/**
 * Interface between `scc-input-tester` tool (and "Register non-steam gamepad"
 * dialog in GUI) and driver, as defined in 'driver.h'.
 *
 * While it may be usefull to have input test in every driver,
 * only generic drivers such as evdev and DirectInput _really_ needs to
 * bother with this. Everything else can just leave 'input_test' field set to NULL.
 */
#pragma once
#ifdef __cplusplus
extern "C" {
#endif
#include "scc/driver.h"

typedef enum TestModeEvent {
	TME_AXIS =		1,
	TME_REL =		2,
	TME_BUTTON =	3,
} TestModeEvent;

typedef void (*controller_available_cb)(const char* driver_name,
					uint8_t confidence, const InputDeviceData* idata);
typedef void (*controller_test_cb)(Controller* c, TestModeEvent event,
					uint32_t code, int64_t data);

typedef struct InputDeviceCapabilities {
	/** Allocated size of 'buttons' array */
	size_t			max_button_count;
	/** Allocated size of 'axes' array */
	size_t			max_axis_count;
	/** Actual size of 'buttons' array */
	size_t			button_count;
	/** Actual size of 'axes' array */
	size_t			axis_count;
	/** Array of button codes */
	uint32_t*		buttons;
	/** Array of axis codes */
	uint32_t*		axes;
} InputDeviceCapabilities;


typedef struct InputTestMethods {
	/**
	 * Called to instruct driver to list all devices it recognizes,
	 * even thought it's not currently configured to use them.
	 *
	 * 'controller_available' callback doesn't have to be called right away.
	 * Instead, registering callbacks with daemon->hotplug_cb_add and waiting
	 * until list of devices is retrieved by daemon (or input tester) may be
	 * necessary.
	 * It's safe to store 'controller_available' callback for later use.
	 *
	 * 'driver_name' controller_available should be set to driver filename,
	 * without "libscc-drv-" prefix and ".so" / ".dll" (or other) suffix.
	 * That means that "libscc-drv-evdev.so" will identify itself as "evdev".
	 *
	 * 'confidence' controller_available argument describes how sure driver
	 * is that device described by 'idata' is game controller.
	 * Scale goes from 9 (definitelly controller) to 0 (definitelly not controller)
	 *
	 * This method is called from scc-input-tester.
	 * May be NULL.
	 */
	void			(*list_devices)(Driver* drv, Daemon* daemon,
							const controller_available_cb controller_available);
	/**
	 * Called to instruct driver to open and start testing given device.
	 * This will be most likelly called from 'controller_available' callback and
	 * driver is expected to call daemon->controller_add method if device is
	 * opened sucesfully but then, instead of supplying data to mapper,
	 * supply changes in controller read-outs using 'test_cb'.
	 *
	 * This method is called from scc-input-tester.
	 * May be NULL.
	 */
	void			(*test_device)(Driver* drv, Daemon* daemon,
							const InputDeviceData* idata,
							const controller_test_cb test_cb);
	/**
	 * Called to ask driver about number of buttons and axes on controller.
	 * 'capabilities' will be preallocated by caller. Method should fill
	 * both 'axes' and 'buttons' arrays and set '*_count' fields,
	 * while respecting 'max_*_count' limits set by caller.
	 *
	 * This method is called from scc-input-tester.
	 * May be NULL.
	 */
	void			(*get_device_capabilities)(Driver* drv, Daemon* daemon,
							const InputDeviceData* idata,
							InputDeviceCapabilities* capabilities);
} InputTestDriver;

#ifdef __cplusplus
}
#endif

