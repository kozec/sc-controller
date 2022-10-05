/**
 * SCC - Steam Deck Driver
 *
 * It looks similar to wired controller driver, but some constants differ.
 *
 * Deck also uses slightly different packed format and so common handle_input
 * is not used.
 *
 * On top of that, deck will automatically enable lizard mode unless requested
 * to not do so periodically.
 */
#define LOG_TAG "deck"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/input_device.h"
#include "scc/input_test.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include "scc/tools.h"
#include "sc.h"
#include <stddef.h>

#define member_size(type, member) sizeof(((type *)0)->member)

#define VENDOR_ID			0x28de
#define PRODUCT_ID			0x1205
#define ENDPOINT			3
#define CONTROLIDX			2
#define PACKET_SIZE			128
#define UNLIZARD_INTERVAL	100
// Counts are used only for scc-input-test
#define BUTTON_COUNT		32
#define AXIS_COUNT			(member_size(ControllerInput, axes) / sizeof(AxisValue))
#define TRIGGER_COUNT		2
// Basically, sticks on deck tend to return to non-zero position
#define STICK_DEADZONE		3000

static controller_available_cb controller_available = NULL;
static controller_test_cb controller_test = NULL;
static ControllerInput* controller_test_last = NULL;


typedef struct DeckInput {
	//    _a1[3]  seq          buttons     lpdx lpdy rpdx rpdy       ????? ??? ??? ? ????? ???? ??? ??  ltrg rtrg  lstick    rstick
	// 01 000940 B1FF0E00 0000100000000000 0000 0000 8E34 48E8 0EFCCD015A410400EEFFFBFF1E7E40006E046015 0000 0000 0000 0000 0000 0000 0000000000000000
	// 01 000940 51BA0D00 0000000000000000 0000 0000 0000 0000 D5FB8E04A63F0200000000004A6A4C01A206FC46 FF7F 0000 0000 0000 0000 0000 0000000000000000
	// 01 000940 5EC40F00 0100000000000000 0000 0000 0000 0000 27016C07003E070020004D00907B4005B202E020 0000 FF7F 0000 0000 0000 0000 0000000000000000
	// 01 000940 5D0C1000 0000000000400000 0000 0000 0000 0000 95FC1504674007FFC3FFFBFF88766AFE6A032630 0000 0000 0D25 8384 0000 0000 0000000028000000
	// 01 000940 967B0D00 0000000000000000 0000 0000 0000 0000 F8FB9604BC3FFFFF010000004A6A4C01A206FC46 0000 0000 0000 0000 FF7F FCED 0000000000005800
	// 01 000940 EB640C00 0000080000000000 44EB 26D6 0000 0000 28FCBAF9DA3DDFFF34002D008E532CFB12FDCC60 0000 0000 0000 0000 4208 0000 0000000000000000
	//                    0000000000000000
	uint8_t			ptype;
	uint8_t			_a1[3];
	uint32_t		seq;
	uint64_t		buttons;
	int16_t			lpad_x;
	int16_t			lpad_y;
	int16_t			rpad_x;
	int16_t			rpad_y;
	
	int16_t			accel_x;
	int16_t			accel_y;
	int16_t			accel_z;
	int16_t			gpitch;
	int16_t			groll;
	int16_t			gyaw;
	int16_t			q1;
	int16_t			q2;
	int16_t			q3;
	int16_t			q4;
	
	uint16_t		ltrig;
	uint16_t		rtrig;
	int16_t			lstick_x;
	int16_t			lstick_y;
	int16_t			rstick_x;
	int16_t			rstick_y;
} DeckInput;


typedef enum DeckButton {
	SDB_DOTS				= 0b100000000000000000000000000000000000000000000000000,	// bit 50
	SDB_RSTICKTOUCH			= 0b000100000000000000000000000000000000000000000000000,	// bit 47
	SDB_LSTICKTOUCH			= 0b000010000000000000000000000000000000000000000000000,	// bit 46
	SDB_RGRIP2				= 0b000000001000000000000000000000000000000000000000000,	// bit 42
	SDB_LGRIP2				= 0b000000000100000000000000000000000000000000000000000,	// bit 41
	SDB_RSTICKPRESS			= 0b000000000000000000000000100000000000000000000000000,	// bit 26
	SDB_LSTICKPRESS			= 0b000000000000000000000000000010000000000000000000000,	// bit 22
	// bit 21 unused?
	SDB_RPADTOUCH			= 0b000000000000000000000000000000100000000000000000000,	// bit 20
	SDB_LPADTOUCH			= 0b000000000000000000000000000000010000000000000000000,
	SDB_RPADPRESS			= 0b000000000000000000000000000000001000000000000000000,
	SDB_LPADPRESS			= 0b000000000000000000000000000000000100000000000000000,	// bit 17
	SDB_RGRIP				= 0b000000000000000000000000000000000010000000000000000,
	SDB_LGRIP				= 0b000000000000000000000000000000000001000000000000000,
	SDB_START				= 0b000000000000000000000000000000000000100000000000000,	// bit 14
	SDB_C					= 0b000000000000000000000000000000000000010000000000000,
	SDB_BACK				= 0b000000000000000000000000000000000000001000000000000,
	SDB_DPAD_DOWN			= 0b000000000000000000000000000000000000000100000000000,	// bit 11
	SDB_DPAD_LEFT			= 0b000000000000000000000000000000000000000010000000000,
	SDB_DPAD_RIGHT			= 0b000000000000000000000000000000000000000001000000000,
	SDB_DPAD_UP				= 0b000000000000000000000000000000000000000000100000000,
	SDB_A					= 0b000000000000000000000000000000000000000000010000000,	// bit 7
	SDB_X					= 0b000000000000000000000000000000000000000000001000000,
	SDB_B					= 0b000000000000000000000000000000000000000000000100000,
	SDB_Y					= 0b000000000000000000000000000000000000000000000010000,
	SDB_LB					= 0b000000000000000000000000000000000000000000000001000,	// bit 3
	SDB_RB					= 0b000000000000000000000000000000000000000000000000100,
	SDB_LT					= 0b000000000000000000000000000000000000000000000000010,
	SDB_RT					= 0b000000000000000000000000000000000000000000000000001,	// bit 0
	_DeckButton_padding = 0xFFFFFFFFFFFFFFFF	// uint64_t
} DeckButton;


static const uint64_t DIRECTLY_TRANSLATABLE_BUTTONS = (0
	| SDB_A | SDB_B | SDB_X | SDB_Y
	| SDB_LB | SDB_RB | SDB_LT | SDB_RT
	| SDB_START | SDB_C | SDB_BACK
	| SDB_RGRIP | SDB_LGRIP
	| SDB_RPADTOUCH | SDB_LPADTOUCH | SDB_RPADPRESS | SDB_LPADPRESS
);


inline static SCButton map_button(DeckInput* i, DeckButton from, SCButton to) {
	return (i->buttons & from) ? to : 0;
}

inline static AxisValue map_dpad(DeckInput* i, DeckButton low, DeckButton hi) {
	return ((i->buttons & low) ? STICK_PAD_MIN : ((i->buttons & hi) ? STICK_PAD_MAX : 0));
}

inline static AxisValue apply_deadzone(AxisValue value, AxisValue deadzone) {
	return ((value > -deadzone) && (value < deadzone)) ? 0 : value;
}


static void handle_deck_input(SCController* sc, DeckInput* i) {
	if (i->seq % UNLIZARD_INTERVAL == 0) {
		// Keeps lizard mode from happening
		clear_mappings(sc);
	}
	
	if ((sc->mapper != NULL) || (controller_test != NULL)) {
		
		// Convert buttons
		SCButton buttons = (0
			| ((i->buttons & DIRECTLY_TRANSLATABLE_BUTTONS) << 8)
			| map_button(i, SDB_DOTS, B_DOTS)
			// | map_button(i, SDB_RSTICKTOUCH, ....)	// not mapped
			// | map_button(i, SDB_LSTICKTOUCH, ....) // not mapped
			| map_button(i, SDB_LSTICKPRESS, B_STICKPRESS)
			| map_button(i, SDB_RSTICKPRESS, B_RSTICKPRESS)
			| map_button(i, SDB_LGRIP2, B_LGRIP2)
			| map_button(i, SDB_RGRIP2, B_RGRIP2)
		);
		sc->input.buttons = buttons;
		
		// Convert triggers
		sc->input.ltrig = i->ltrig >> 7;
		sc->input.rtrig = i->rtrig >> 7;
		
		// Copy axes
		sc->input.stick_x = apply_deadzone(i->lstick_x, STICK_DEADZONE);
		sc->input.stick_y = apply_deadzone(i->lstick_y, STICK_DEADZONE);
		sc->input.rstick_x = apply_deadzone(i->rstick_x, STICK_DEADZONE);
		sc->input.rstick_y = apply_deadzone(i->rstick_y, STICK_DEADZONE);
		sc->input.lpad_x = i->lpad_x;  // TODO: is memcpy faster here?
		sc->input.lpad_y = i->lpad_y;  // TODO: is memcpy faster here?
		sc->input.rpad_x = i->rpad_x;  // TODO: is memcpy faster here?
		sc->input.rpad_y = i->rpad_y;  // TODO: is memcpy faster here?
		
		// Copy gyro
		static_assert(sizeof(GyroValue) == sizeof(int16_t));
		memcpy(&sc->input.gyro, &i->accel_x, sizeof(GyroInput));
		
		// Handle dpad
		sc->input.dpad_x = map_dpad(i, SDB_DPAD_LEFT, SDB_DPAD_RIGHT);
		sc->input.dpad_y = map_dpad(i, SDB_DPAD_DOWN, SDB_DPAD_UP);
		
		if (controller_test != NULL) {
			uint32_t i;
			for (i = 0; i < member_size(ControllerInput, axes) / sizeof(AxisValue); i++) {
				if (controller_test_last->axes[i] != sc->input.axes[i]) {
					controller_test_last->axes[i] = sc->input.axes[i];
					controller_test(&sc->controller, TME_AXIS, i, sc->input.axes[i]);
				}
			}
			for (i = 0; i < 2; i++) {
				if (controller_test_last->triggers[i] != sc->input.triggers[i]) {
					controller_test_last->triggers[i] = sc->input.triggers[i];
					controller_test(&sc->controller, TME_AXIS, AXIS_COUNT + i, sc->input.triggers[i]);
				}
			}
			for (i = 0; i < BUTTON_COUNT; i ++) {
				if ((sc->input.buttons & (1 << i)) != (controller_test_last->buttons & (1 << i))) {
					controller_test(&sc->controller, TME_BUTTON, i, (sc->input.buttons & (1 << i)) ? 1 : 0);
				}
			}
			controller_test_last->buttons = sc->input.buttons;
		} else {
			sc->mapper->input(sc->mapper, &sc->input);
		}
	}
}


void input_interrupt_cb(Daemon* d, InputDevice* dev, uint8_t endpoint, const uint8_t* data, void* userdata) {
	SCController* sc = (SCController*)userdata;
	if (data == NULL) {
		// Means some kind of failure. Deck can't exactly disconnect, so this is
		// left mostly just in case
		DEBUG("%s disconnected", sc->desc);
		disconnected(sc);
		// TODO: Deallocate sc
		return;
	}
	
	DeckInput* i = (DeckInput*)data;
	if (i->ptype == PT_INPUT)
		handle_deck_input(sc, i);
}

static const char* get_type(Controller* c) {
	return "deck";
}


static bool deck_configure(SCController* sc, uint8_t* data) {
	uint8_t buffer[64] = { 0 };
	uint8_t len = data[1] + 2;
	memcpy(buffer, data, len);
	if (sc->dev != NULL)
		if (!sc->dev->hid_request(sc->dev, sc->idx, buffer, -64) == 0)
			return true;
	return false;
}


static void open_device(Daemon* daemon, const InputDeviceData* idata) {
	// TODO: unify all that open_device bs
	SCController* sc = NULL;
	InputDevice* dev = idata->open(idata);
	if (dev == NULL) {
		LERROR("Failed to open '%s'", idata->path);
		return;
	}
	if ((sc = create_usb_controller(daemon, dev, SC_DECK, CONTROLIDX)) == NULL) {
		LERROR("Failed to allocate memory");
		goto open_device_fail;
	}
	if (dev->claim_interfaces_by(dev, 3, 0, 0) <= 0) {
		LERROR("Failed to claim interfaces");
		goto open_device_fail;
	}
	if (!configure(sc))
		goto open_device_failed_to_configure;
	if (!clear_mappings(sc))
		goto open_device_failed_to_configure;
	if (!read_serial(sc)) {
		LERROR("Failed to read serial number");
		goto open_device_failed_to_configure;
	}
	
	if (!dev->interupt_read_loop(dev, ENDPOINT, PACKET_SIZE, &input_interrupt_cb, sc)) {
		LERROR("interupt_read_loop failed");
		goto open_device_failed_to_configure;
	}
	
	DEBUG("Steam Deck with serial %s sucesfully configured", sc->serial);
	sc->state = SS_READY;
	sc->controller.get_type = &get_type;
	if (!daemon->controller_add(&sc->controller)) {
		// This shouldn't happen unless memory is running out
		DEBUG("Failed to add deck to daemon");
		goto open_device_fail;
	}
	return;
	
open_device_failed_to_configure:
	LERROR("Failed to configure deck");
open_device_fail:
	if (sc != NULL)
		free(sc);
	dev->close(dev);
}


static bool hotplug_cb(Daemon* daemon, const InputDeviceData* idata) {
	if (controller_available != NULL) {
		controller_available("steamdeck", 9, idata);
	} else {
		open_device(daemon, idata);
	}
	return true;
}


static bool driver_start(Driver* drv, Daemon* daemon) {
	HotplugFilter filter_vendor  = { .type=SCCD_HOTPLUG_FILTER_VENDOR,	.vendor=VENDOR_ID };
	HotplugFilter filter_product = { .type=SCCD_HOTPLUG_FILTER_PRODUCT,	.product=PRODUCT_ID };
	HotplugFilter filter_idx	 = { .type=SCCD_HOTPLUG_FILTER_IDX,		.idx=CONTROLIDX };
	// Subsystem s = daemon->get_hidapi_enabled() ? HIDAPI : USB;
	Subsystem s = USB;
#if defined(_WIN32)
	#define FILTERS &filter_vendor, &filter_product, &filter_idx
#elif defined(__BSD__)
	#define FILTERS &filter_vendor, &filter_product, &filter_idx
	s = UHID;
#else
	// NOTE: if &filter_idx is included, USB mode fails to find dev
	// NOTE: if &filter_idx is excluded, HIDAPI mode fails to find dev
	#define FILTERS &filter_vendor, &filter_product
#endif
	if (!daemon->hotplug_cb_add(s, hotplug_cb, FILTERS, NULL)) {
		LERROR("Failed to register hotplug callback");
		return false;
	}
	return true;
}


static void driver_list_devices(Driver* drv, Daemon* daemon, const controller_available_cb ca) {
	controller_available = ca;
	driver_start(drv, daemon);
}

static void driver_get_device_capabilities(Driver* drv, Daemon* daemon,
									const InputDeviceData* idev,
									InputDeviceCapabilities* capabilities) {
	capabilities->button_count = 31;
	capabilities->axis_count = AXIS_COUNT + 2;
	for (int i = 0; i < capabilities->button_count; i++)
		capabilities->buttons[i] = i;
	for (int i = 0; i < capabilities->axis_count; i++)
		capabilities->axes[i] = i;
}

static void driver_test_device(Driver* drv, Daemon* daemon,
			const InputDeviceData* idata,  const controller_test_cb test_cb) {
	controller_test = test_cb;
	if (controller_test_last == NULL) {
		controller_test_last = calloc(1, sizeof(ControllerInput));
		if (controller_test_last == NULL) {
			LERROR("driver_test_device: out of memory");
			return;
		}
	}
	open_device(daemon, idata);
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

