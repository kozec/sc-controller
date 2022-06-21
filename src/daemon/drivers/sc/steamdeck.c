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

#define VENDOR_ID			0x28de
#define PRODUCT_ID			0x1205
#define ENDPOINT			3
#define CONTROLIDX			2
#define PACKET_SIZE			128
#define UNLIZARD_INTERVAL	500

static controller_available_cb controller_available = NULL;


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
	uint8_t			_a2[20];
	uint16_t		ltrig;
	uint16_t		rtrig;
	int16_t			lstick_x;
	int16_t			lstick_y;
	int16_t			rstick_x;
	int16_t			rstick_y;
	/*int16_t			accel_x;
	int16_t			accel_y;
	int16_t			accel_z;
	int16_t			gpitch;
	int16_t			groll;
	int16_t			gyaw;
	*/
	int16_t			q1;
	int16_t			q2;
	int16_t			q3;
	int16_t			q4;
	uint8_t			_a3[8];
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


static char* int_to_bin(uint64_t k, uint64_t* last) {
	static char bits[65] = {' '};
	uint64_t j = 1;
	for (uint64_t i=0; i<64; i++) {
		bits[64-i] = '.';
		if (k & j) {
			bits[64-i] = '1';
			*last = i;
		}
		j <<= 1;
	}
	return bits;
}


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


static void handle_deck_input(SCController* sc, DeckInput* i) {
	if (sc->mapper != NULL) {
		if (i->seq % UNLIZARD_INTERVAL == 0) {
			// Keeps lizard mode from happening
			clear_mappings(sc);
		}
		
		SCButton buttons = (0
			| ((i->buttons & DIRECTLY_TRANSLATABLE_BUTTONS) << 8)
			| map_button(i, SDB_DOTS, B_DOTS)
			// | map_button(i, SDB_RSTICKTOUCH, ....)	// not mapped
			// | map_button(i, SDB_LSTICKTOUCH, ....) // not mapped
			| map_button(i, SDB_RSTICKPRESS, B_STICKPRESS)
			| map_button(i, SDB_LSTICKPRESS, B_LSTICKPRESS)
			| map_button(i, SDB_LGRIP2, B_LGRIP2)
			| map_button(i, SDB_RGRIP2, B_RGRIP2)
		);
		
		sc->input.stick_x = i->lstick_x;
		sc->input.stick_y = i->lstick_y;
		sc->input.cpad_x = i->rstick_x;
		sc->input.cpad_y = i->rstick_y;
		sc->input.lpad_x = i->lpad_x;  // TODO: is memcpy faster here?
		sc->input.lpad_y = i->lpad_y;  // TODO: is memcpy faster here?
		sc->input.rpad_x = i->rpad_x;  // TODO: is memcpy faster here?
		sc->input.rpad_y = i->rpad_y;  // TODO: is memcpy faster here?
		sc->input.ltrig = i->ltrig >> 7;
		sc->input.rtrig = i->rtrig >> 7;
		
		// uint64_t last = 0;
		// char* b = int_to_bin(i->buttons, &last);
		// LOG("B %s %li %x %x %lx", b, last, sc->input.ltrig, sc->input.rtrig, i->buttons);
		
		/*
		SCButton buttons = (((SCButton)i->buttons1) << 24) | (((SCButton)i->buttons0) << 8);
		bool lpadtouch = buttons & B_LPADTOUCH;
		bool sticktilt = buttons & B_STICKTILT;
		if (lpadtouch & !sticktilt)
			sc->input.stick_x = sc->input.stick_y = 0;
		else if (!lpadtouch)
			memcpy(&sc->input.stick_x, &i->lpad_x, sizeof(AxisValue) * 2);
		if (!(lpadtouch || sticktilt))
			sc->input.lpad_x = sc->input.lpad_y = 0;
		else if (lpadtouch)
			memcpy(&sc->input.lpad_x, &i->lpad_x, sizeof(AxisValue) * 2);
		
		if (buttons & B_LPADPRESS) {
			// LPADPRESS button may signalize pressing stick instead
			if ((buttons & B_STICKPRESS) && !(buttons & B_STICKTILT))
				buttons &= ~B_LPADPRESS;
		}
		// Steam controller computes and sends dpad "buttons" as well, but
		// SC Controller doesn't use them, so they are zeroed here
		*/
		sc->input.buttons = buttons;
		sc->mapper->input(sc->mapper, &sc->input);
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
		if (!sc->dev->hid_request(sc->dev, sc->idx, buffer, -64) == NULL)
			return true;
	return false;
}


static bool hotplug_cb(Daemon* daemon, const InputDeviceData* idata) {
	if (controller_available != NULL) {
		controller_available("deck", 9, idata);
		return true;
	}
	SCController* sc = NULL;
	InputDevice* dev = idata->open(idata);
	if (dev == NULL) {
		LERROR("Failed to open '%s'", idata->path);
		return true;		// and nothing happens
	}
	if ((sc = create_usb_controller(daemon, dev, SC_DECK, CONTROLIDX)) == NULL) {
		LERROR("Failed to allocate memory");
		goto hotplug_cb_fail;
	}
	if (dev->claim_interfaces_by(dev, 3, 0, 0) <= 0) {
		LERROR("Failed to claim interfaces");
		goto hotplug_cb_fail;
	}
	if (!configure(sc))
		goto hotplug_cb_failed_to_configure;
	if (!clear_mappings(sc))
		goto hotplug_cb_failed_to_configure;
	if (!read_serial(sc)) {
		LERROR("Failed to read serial number");
		goto hotplug_cb_failed_to_configure;
	}
	
	if (!dev->interupt_read_loop(dev, ENDPOINT, PACKET_SIZE, &input_interrupt_cb, sc)) {
		LERROR("interupt_read_loop failed");
		goto hotplug_cb_failed_to_configure;
	}
	
	DEBUG("Steam Deck with serial %s sucesfully configured", sc->serial);
	sc->state = SS_READY;
	sc->controller.get_type = &get_type;
	if (!daemon->controller_add(&sc->controller)) {
		// This shouldn't happen unless memory is running out
		DEBUG("Failed to add deck to daemon");
		goto hotplug_cb_fail;
	}
	return true;
hotplug_cb_failed_to_configure:
	LERROR("Failed to configure deck");
hotplug_cb_fail:
	if (sc != NULL)
		free(sc);
	dev->close(dev);
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

static Driver driver = {
	.unload = NULL,
	.start = driver_start,
	// .list_devices = driver_list_devices,
};

Driver* scc_driver_init(Daemon* daemon) {
	ASSERT(sizeof(TriggerValue) == 1);
	ASSERT(sizeof(AxisValue) == 2);
	ASSERT(sizeof(GyroValue) == 2);
	// ^^ If any of above assertions fails, input_interrupt_cb code has to be
	//    modified so it doesn't use memcpy calls, as those depends on those sizes
	
	return &driver;
}

