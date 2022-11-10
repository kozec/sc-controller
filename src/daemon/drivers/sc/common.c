#define LOG_TAG "sc"
#include "scc/utils/container_of.h"
#include "scc/utils/logging.h"
#include "scc/utils/rc.h"
#include "scc/input_device.h"
#include "scc/mapper.h"
#include "scc/driver.h"
#include "scc/config.h"
#include "sc.h"
#include <stddef.h>
#include <string.h>

#define B_STICKTILT			0b10000000000000000000000000000000
#define BUFFER_SIZE			128
#define SMALL_BUFFER_SIZE	64

static const char* get_description(Controller* c);
static const char* get_type(Controller* c);
static const char* get_id(Controller* c);
static void set_mapper(Controller* c, Mapper* m);
static void set_gyro_enabled(Controller* c, bool enabled);
static bool get_gyro_enabled(Controller* c);
static void haptic_effect(Controller* c, HapticData* hdata);
static void flush(Controller* c, Mapper* m);

static uint64_t used_serials = 0;

void handle_input(SCController* sc, SCInput* i) {
	if (sc->mapper != NULL) {
		memcpy(&sc->input.ltrig, &i->ltrig, sizeof(TriggerValue) * 2);
			memcpy(&sc->input.rpad_x, &i->rpad_x, sizeof(AxisValue) * 2);
			memcpy(&sc->input.gyro, &i->accel_x, sizeof(struct GyroInput));
			
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
			buttons &= ~0b00000000000011110000000000000000;
			sc->input.buttons = buttons;
			sc->mapper->input(sc->mapper, &sc->input);
	}
}

static void deallocate(Controller* c) {
	SCController* sc = container_of(c, SCController, controller);
	if (sc->dev != NULL)
		sc->dev->close(sc->dev);
	free(sc);
}

void disconnected(SCController* sc) {
	sc->dev = NULL;
	if (sc->state == SS_READY) {
		if (sc->mapper != NULL) {
			// Releases all buttons, centers all sticks and sends fake input to mapper
			memset(&sc->input, 0, sizeof(ControllerInput));
			sc->mapper->input(sc->mapper, &sc->input);
		}
		sc->state = SS_FAILED;
		sc->daemon->controller_remove(&sc->controller);
	}
}


static void deallocate_dongle_controller(Controller* c) {
	// TODO: This. It will need reference count of some sort
	// SCController* sc = container_of(c, SCController, controller);
	// free(sc);
}

SCController* create_usb_controller(Daemon* daemon, InputDevice* dev, SCControllerType type, uint16_t idx) {
	SCController* sc = malloc(sizeof(SCController));
	if (sc == NULL)
		return NULL;
	memset(sc, 0, sizeof(SCController));
	sc->controller.flags = CF_NO_FLAGS;
	sc->controller.get_id = &get_id;
	sc->controller.get_type = &get_type;
	sc->controller.get_description = &get_description;
	sc->controller.haptic_effect = &haptic_effect;
	sc->controller.turnoff = NULL;
	sc->controller.flush = &flush;
	sc->controller.set_mapper = &set_mapper;
	sc->controller.set_gyro_enabled = &set_gyro_enabled;
	sc->controller.get_gyro_enabled = &get_gyro_enabled;
	// Main difference between dongle-bound and wired controller is that dongle-bound
	// countroller doesn't close USB device when deallocated
	sc->controller.deallocate = (type == SC_WIRED) ? &deallocate : &deallocate_dongle_controller;
	
	HAPTIC_DISABLE(&sc->hdata[0]); sc->hdata[0].pos = HAPTIC_LEFT;
	HAPTIC_DISABLE(&sc->hdata[1]); sc->hdata[1].pos = HAPTIC_RIGHT;
	sc->state = SS_NOT_CONFIGURED;
	sc->gyro_enabled = true;
	sc->dev = dev;
	sc->daemon = daemon;
	sc->auto_id_used = false;
	sc->idle_timeout = 10 * 60;		// 10 minutes
	sc->led_level = 50;
	sc->type = type;
	sc->long_packet = 0;
	sc->idx = idx;
	return sc;
}

static const char* get_id(Controller* c) {
	SCController* sc = container_of(c, SCController, controller);
	return sc->id;
}

static const char* get_type(Controller* c) {
	return "sc";
}

static const char* get_description(Controller* c) {
	SCController* sc = container_of(c, SCController, controller);
	return sc->desc;
}

static void set_mapper(Controller* c, Mapper* m) {
	SCController* sc = container_of(c, SCController, controller);
	sc->mapper = m;
}

static void	set_gyro_enabled(Controller* c, bool enabled) {
	SCController* sc = container_of(c, SCController, controller);
	sc->gyro_enabled = enabled;
	configure(sc);
}

static bool get_gyro_enabled(Controller* c) {
	SCController* sc = container_of(c, SCController, controller);
	return sc->gyro_enabled;
}

static inline void haptic_effect_add(HapticData* target, HapticData* src) {
	uint32_t a = (uint32_t)target->amplitude + (uint32_t)src->amplitude;
	uint32_t p = (target->period == 0) ? src->period : ((uint32_t)target->period + (uint32_t)src->period) / 2;
	if (a > 0xFFFF) a = 0xFFFF;
	if (p > 0xFFFF) p = 0xFFFF;
	target->amplitude = a;
	target->period = p;
}

static void haptic_effect(Controller* c, HapticData* hdata) {
	SCController* sc = container_of(c, SCController, controller);
	if ((hdata->pos == HAPTIC_RIGHT) || (hdata->pos == HAPTIC_BOTH))
		haptic_effect_add(&sc->hdata[0], hdata);
	if ((hdata->pos == HAPTIC_LEFT) || (hdata->pos == HAPTIC_BOTH))
		haptic_effect_add(&sc->hdata[1], hdata);
}

static union {
	uint8_t		bytes[BUFFER_SIZE];
	struct __attribute__((__packed__)) {
		uint8_t		packet_type;
		uint8_t		len;
		uint8_t		position;
		uint16_t	amplitude;
		uint16_t	period;
		uint16_t	cunt;
	};
//TODO need change for BT?
} haptic = { .packet_type = PT_FEEDBACK, .len = PL_FEEDBACK, .cunt = 1 };

/**
 * Haptic events generated by timers or durring 'input' phase are merged
 * together and flushed out at once.
 */
static void flush(Controller* c, Mapper* m) {
	SCController* sc = (SCController*)c;
	for (uint8_t i=0; i<=1; i++) {
		if (HAPTIC_ENABLED(&sc->hdata[i])) {
			haptic.position = i;
			haptic.amplitude = sc->hdata[i].amplitude;
			haptic.period = sc->hdata[i].period;
#ifdef _WIN32
			// Special case, windows needs to do this synchronously
			// using hid_request, or it throws "overlapped operation in progress"
			// error.
			//TODO need change for BT?
			haptic.packet_type = PT_FEEDBACK;
			haptic.len = PL_FEEDBACK;
			haptic.cunt = 1;
			sc->dev->hid_request(sc->dev, sc->idx, haptic.bytes, -64);
#else
			sc->dev->hid_write(sc->dev, sc->idx, haptic.bytes, 64);
#endif
		}
		HAPTIC_DISABLE(&sc->hdata[i]);
	}
}


static void update_desc(SCController* sc) {
	switch (sc->type) {
	case SC_WIRED:
		snprintf(sc->desc, MAX_DESC_LEN, "<SCByCable %s>", sc->serial);
		break;
	case SC_WIRELESS:
		snprintf(sc->desc, MAX_DESC_LEN, "<SC %s>", sc->serial);
		break;
	case SC_BT:
		snprintf(sc->desc, MAX_DESC_LEN, "<SCByBt %s>", sc->serial);
		break;
	case SC_DECK:
		snprintf(sc->desc, MAX_DESC_LEN, "<Deck %s>", sc->serial);
		break;
	}
}

static inline void debug_packet(char* buffer, size_t size) {
	size_t i;
	for(i=0; i<size; i++)
		printf("%02x", buffer[i] & 0xff);
	DDEBUG("\n");
}

bool read_serial(SCController* sc) {
	Config* c = config_load();
	if ((c != NULL) && (config_get_int(c, "ignore_serials") == 1)) {
		// Special exception for cases when controller drops instead of
		// sending serial number. See issue #103
		int i = 0;
		for (; i<64; i++) {
			if ((used_serials & (1 << i)) == 0)
				break;
		}
		used_serials |= (1 << i);
		sc->auto_id_used = true;
		sc->auto_id = i;
		snprintf(sc->serial, MAX_SERIAL_LEN, "%d", i);
		if (sc->type == SC_DECK)
			snprintf(sc->id, MAX_ID_LEN, "deck%s", sc->serial);
		else
			snprintf(sc->id, MAX_ID_LEN, "sc%s", sc->serial);
		update_desc(sc);
		RC_REL(c);
		return true;
	}
	RC_REL(c);
	
//ephemeral extra bit at end (?) of buffer on windows only
#ifdef _WIN32
	int data_size = sc->type == SC_BT ? BUFFER_SIZE : (SMALL_BUFFER_SIZE + 1);
#else
	int data_size = sc->type == SC_BT ? BUFFER_SIZE : (SMALL_BUFFER_SIZE);
#endif
	int bt_offset = 0;
	uint8_t* response;
	uint8_t* data; 
	if(sc->type == SC_BT){
		data = calloc(data_size, sizeof(uint8_t));
		data[0] = PT_BT_PREFIX;
		data[1] = PT_GET_SERIAL;
		data[2] = PL_GET_SERIAL;
	    data[3] = 0x01;
		bt_offset = 2;
	} else {
		//TODO expand to 128 okay?
		data = calloc(data_size, sizeof(uint8_t));
		data[0] = PT_GET_SERIAL;
	    data[1] = PL_GET_SERIAL;
	    data[2] = 0x01;
	}

	if(sc->type == SC_BT){
#ifdef _WIN32
		response = sc->dev->hid_request(sc->dev, sc->idx, data, -(SMALL_BUFFER_SIZE + 1));
#else
		response = sc->dev->hid_request(sc->dev, sc->idx, data, -(SMALL_BUFFER_SIZE));
#endif
	} else {
		response = sc->dev->hid_request(sc->dev, sc->idx, data, -SMALL_BUFFER_SIZE);
	}
	if (response == NULL) {
		LERROR("Failed to retrieve serial number");
		return false;
	}
	if (sc->type != SC_BT && (data[0] != PT_GET_SERIAL) && (data[1] != PL_GET_SERIAL)) {
		// Sometimes, freshly connected controller is not able to send its own
		// serial straight away
		return false;
	} 
	if (sc->type == SC_BT && data[4] == 0) {
		//TODO flush so don't have to reset controller
		debug_packet((char *)data, data_size);
		return false;
	}
	data[13 + bt_offset] = 0;	// to terminate string
	debug_packet((char *)data, data_size);
	strncpy(sc->serial, (const char*) &data[3 + bt_offset], MAX_SERIAL_LEN);
	if (sc->type == SC_DECK)
		snprintf(sc->id, MAX_ID_LEN, "deck%s", sc->serial);
	else
		snprintf(sc->id, MAX_ID_LEN, "sc%s", sc->serial);
	update_desc(sc);
	
	return true;
}

bool lizard_mode(SCController* sc) {
	uint8_t data[BUFFER_SIZE] = { PT_LIZARD_BUTTONS, 0x01 };
	if (sc->dev->hid_request(sc->dev, sc->idx, data, -64) == NULL) {
		LERROR("Failed to activate lizard mode");
		return false;
	}
	data[0] = PT_LIZARD_MOUSE;
	if (sc->dev->hid_request(sc->dev, sc->idx, data, -64) == NULL) {
		LERROR("Failed to activate lizard mode");
		return false;
	}
	return true;
}

bool clear_mappings(SCController* sc) {
	uint8_t* data; 
#ifdef _WIN32
	int data_size = sc->type == SC_BT ? BUFFER_SIZE : (SMALL_BUFFER_SIZE + 1);
#else
	int data_size = sc->type == SC_BT ? BUFFER_SIZE : (SMALL_BUFFER_SIZE);
#endif
	int bt_offset = 0;
	if(sc->type == SC_BT){
		data = calloc(data_size, sizeof(uint8_t));
		data[0] = PT_BT_PREFIX;
		data[1] = PT_CLEAR_MAPPINGS;
		data[2] = 0x01;
		bt_offset = 2;
	} else {
		//TODO expand to 128 okay?
		data = calloc(data_size, sizeof(uint8_t));
		data[0] = PT_CLEAR_MAPPINGS;
	    data[1] = 0x01;
	}

	if(sc->type == SC_BT){
#ifdef _WIN32
		if (sc->dev->hid_request(sc->dev, sc->idx, data, -(SMALL_BUFFER_SIZE+1)) == NULL){
#else
		if (sc->dev->hid_request(sc->dev, sc->idx, data, -(SMALL_BUFFER_SIZE)) == NULL){
#endif
			LERROR("Failed to clear mappings");
			return false;
		}
	} else {
		if (sc->dev->hid_request(sc->dev, sc->idx, data, -SMALL_BUFFER_SIZE) == NULL){
			LERROR("Failed to clear mappings");
			return false;
		}
	}
	return true;
}

bool configure(SCController* sc) {
	int bt_offset = 0;
#ifdef _WIN32
	int data_size = sc->type == SC_BT ? BUFFER_SIZE : (SMALL_BUFFER_SIZE + 1);
#else
	int data_size = sc->type == SC_BT ? BUFFER_SIZE : (SMALL_BUFFER_SIZE);
#endif

	if (sc->dev == NULL)
		// Special case, controller was disconnected, but it's not deallocated yet
		goto configure_fail;
	if (sc->type == SC_DECK) {
		uint8_t deck_configure[BUFFER_SIZE] = { PT_CONFIGURE, 0x03, 0x08, 0x07 };
		if (sc->dev->hid_request(sc->dev, sc->idx, deck_configure, -64) == NULL)
			goto configure_fail;
	} else if (sc->type == SC_BT) {
		DDEBUG("configuring BT");

#ifdef _WIN32
		uint8_t gyro_and_timeout[SMALL_BUFFER_SIZE + 1] = {
#else
		uint8_t gyro_and_timeout[SMALL_BUFFER_SIZE] = {
#endif
			// Header 
			// 0x87 0x0f 0x18
			PT_BT_PREFIX, PT_CONFIGURE, PL_CONFIGURE_BT, CONFIGURE_BT,
			// Idle timeout
			//TODO write IDLE timeout(?)
			//(uint8_t)(sc->idle_timeout & 0xFF), (uint8_t)((sc->idle_timeout & 0xFF00) >> 8),
			// unknown1
			0x00, 0x00, 0x31, 0x02, 0x00, 0x08, 0x07, 0x00, 0x07, 0x07, 0x00, 0x30,
			// Gyros
			(sc->gyro_enabled ? 0x14 : 0),
			// unknown2:
			0x00, 0x2e,
		};
		uint8_t leds[65] = { PT_BT_PREFIX, PT_CONFIGURE, PL_LED, CT_LED, sc->led_level };
#ifdef _WIN32
		if (sc->dev->hid_request(sc->dev, sc->idx, gyro_and_timeout, -(SMALL_BUFFER_SIZE + 1)) == NULL)
			goto configure_fail;
		if (sc->dev->hid_request(sc->dev, sc->idx, leds, -(SMALL_BUFFER_SIZE + 1)) == NULL)
			goto configure_fail;
#else
		if (sc->dev->hid_request(sc->dev, sc->idx, gyro_and_timeout, -(SMALL_BUFFER_SIZE)) == NULL)
			goto configure_fail;
		if (sc->dev->hid_request(sc->dev, sc->idx, leds, -(SMALL_BUFFER_SIZE)) == NULL)
			goto configure_fail;
#endif
		bt_offset = 2;
	} else {
		uint8_t leds[BUFFER_SIZE] = { PT_CONFIGURE, PL_LED, CT_LED, sc->led_level };
		uint8_t gyro_and_timeout[BUFFER_SIZE] = {
			// Header
			PT_CONFIGURE, PL_CONFIGURE, CT_CONFIGURE,
			// Idle timeout
			(uint8_t)(sc->idle_timeout & 0xFF), (uint8_t)((sc->idle_timeout & 0xFF00) >> 8),
			// unknown1
			0x18, 0x00, 0x00, 0x31, 0x02, 0x00, 0x08, 0x07, 0x00, 0x07, 0x07, 0x00, 0x30,
			// Gyros
			(sc->gyro_enabled ? 0x1c : 0),
			// unknown2:
			0x00, 0x2e,
		};
		if (sc->dev->hid_request(sc->dev, sc->idx, gyro_and_timeout, -64) == NULL)
			goto configure_fail;
		if (sc->dev->hid_request(sc->dev, sc->idx, leds, -64) == NULL)
			goto configure_fail;
	}
	return true;
configure_fail:
	LERROR("Failed to configure controller");
	return false;
}

