/**
 * Steam Controller Controller Steam Controller Driver
 *
 * Used to communicate with single Steam Controller
 * connected via bluetooth.
 */
#define LOG_TAG "sc_by_bt"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/input_device.h"
#include "scc/input_test.h"
#include "scc/driver.h"
#include "scc/mapper.h"
#include "scc/tools.h"
#include "sc.h"
#include <stddef.h>

#define ENDPOINT			3
#define CONTROLIDX			-1
#define CHUNK_LENGTH		64
#define VENDOR_ID			0x28de
#define PRODUCT_ID			0x1106
#define PACKET_SIZE 		20
#define LONG_PACKET 		0x80
#define BT_BUTTONS_BITS 	23

static controller_available_cb controller_available = NULL;

enum BtInPacketType {
	BUTTON   = 0x0010,
	TRIGGERS = 0x0020,
	STICK    = 0x0080,
	LPAD     = 0x0100,
	RPAD     = 0x0200,
	GYRO     = 0x1800,
	PING     = 0x5000,
};

static inline void debug_packet(char* buffer, size_t size) {
	size_t i;
	for(i=0; i<size; i++)
		printf("%02x", buffer[i] & 0xff);
	DDEBUG("\n");
}

char tmp_buffer[256] = "";
char ptr_buffer[256] = "";	

int bt_handle_input(SCController *sc, uint8_t* i){
	if(sc->mapper != NULL){			
			if (sc->long_packet) {
				// Previous packet had long flag set and this is its 2nd part
				memcpy(ptr_buffer + PACKET_SIZE, tmp_buffer + 1, PACKET_SIZE - 1);
				sc->long_packet = 0;
			} else {
				// This is 1st part of long packet
				memcpy(ptr_buffer, (void *)i, PACKET_SIZE);
				sc->long_packet = *((uint8_t*)(ptr_buffer + 1)) == LONG_PACKET;
				if (sc->long_packet) {
					return 0;
				}
				// debug_packet(ptr->buffer, PACKET_SIZE);
			}
						
			int rv = 0;
			int bit;
			uint16_t type = *((uint16_t*)(ptr_buffer + 2));
			char* data = &ptr_buffer[4];
			if ((type & PING) == PING) {
				// PING packet does nothing
				return 0;
			}
			if ((type & BUTTON) == BUTTON) {
				rv = 1; 
				uint32_t bt_buttons = *((uint32_t*)data);
				uint32_t sc_buttons = 0;
				//TODO cover remaining bits
				for (bit=0; bit<BT_BUTTONS_BITS; bit++) {
					if ((bt_buttons & 1) != 0)
						sc_buttons |= BT_BUTTONS[bit];
					bt_buttons >>= 1;
				}
				sc->input.buttons = (SCButton)sc_buttons;
				data += 3;
			}
			if ((type & TRIGGERS) == TRIGGERS) {
				rv = 1;
				sc->input.ltrig = *(((uint8_t*)data) + 0);
				sc->input.rtrig = *(((uint8_t*)data) + 1);
				data += 2;
			}
			if ((type & STICK) == STICK) {
				rv = 1; 
				sc->input.stick_x = *(((int16_t*)data) + 0);
				sc->input.stick_y = *(((int16_t*)data) + 1);
				data += 4;
			}
			if ((type & LPAD) == LPAD) { 
				rv = 1; 
				sc->input.lpad_x = *(((int16_t*)data) + 0);
				sc->input.lpad_y = *(((int16_t*)data) + 1);
				data += 4;
			}
			if ((type & RPAD) == RPAD) {
				rv = 1;
				sc->input.rpad_x = *(((int16_t*)data) + 0);
				sc->input.rpad_y = *(((int16_t*)data) + 1);
				data += 4;
			}
			if ((type & GYRO) == GYRO) {
				rv = 1; 
				sc->input.gyro.gpitch = *(((int16_t*)data) + 0);
				sc->input.gyro.groll = *(((int16_t*)data) + 1);
				sc->input.gyro.gyaw = *(((int16_t*)data) + 2);
				sc->input.gyro.q0 = *(((int16_t*)data) + 3);
				sc->input.gyro.q1 = *(((int16_t*)data) + 4);
				sc->input.gyro.q2 = *(((int16_t*)data) + 5);
				sc->input.gyro.q3 = *(((int16_t*)data) + 6);
				data += 14;
			}
			sc->input.buttons &= ~0b00000000000011110000000000000000;
			//input eval same bitmap?
			//sc->mapper->input(sc->mapper, &sc->input);
			return rv;
		}
}

void input_interrupt_cb(Daemon* d, InputDevice* dev, uint8_t endpoint, const uint8_t* data, void* userdata) {
	SCController* sc = (SCController*)userdata;
	if (data == NULL) {
		// Means controller disconnected (or failed in any other way)
		DEBUG("%s disconnected", sc->desc);
		// USBHelper* usb = d->get_usb_helper();
		// usb->close(sc->usb_hndl);
		// TODO: Calling close at this point may hang. Closing should be
		//       scheduled for later time instead, ideally in sccd_usb_dev_close.
		disconnected(sc);
		// TODO: Deallocate sc
		return;
	}
	//debug_packet((char *)data, PACKET_SIZE * 2);
	int status = bt_handle_input(sc, data);
	if(status == 1){
		//TODO input rotation support
		/*if (
			//self._input_rotation_l and 
			(self._state.type & 0x0100) != 0) {
			lx, ly = self._state.lpad_x, self._state.lpad_y
			//s, c = sin(self._input_rotation_l), cos(self._input_rotation_l)
			self._state.lpad_x = int(lx * c - ly * s)
			self._state.lpad_y = int(lx * s + ly * c)
		}
		if (
			//self._input_rotation_r and 
			(self._state.type & 0x0200) != 0) {
			rx, ry = self._state.rpad_x, self._state.rpad_y
			s, c = sin(self._input_rotation_r), cos(self._input_rotation_r)
			self._state.rpad_x = int(rx * c - ry * s)
			self._state.rpad_y = int(rx * s + ry * c)
		}*/
		
		sc->mapper->input(sc->mapper, &sc->input);

		//it's unlikely this is necessary
		//flush()
	} else if(status > 1) {
		DDEBUG("Read Failed");

		//TODO maybe should retry
		//self.close()
		//self.driver.retry(self.syspath)
	}	
}


static bool hotplug_cb(Daemon* daemon, const InputDeviceData* idata) {
	if (controller_available != NULL) {
		controller_available("sc_by_bt", 9, idata);
		return true;
	}
	SCController* sc = NULL;
	DDEBUG("%s",idata->path);
	InputDevice* 	dev = idata->open(idata);
	if (dev == NULL) {
		LERROR("Failed to open '%s'", idata->path);
		return true;		// and nothing happens
	}
	if ((sc = create_usb_controller(daemon, dev, SC_BT, CONTROLIDX)) == NULL) {
		LERROR("Failed to allocate memory");
		goto hotplug_cb_fail;
	}
	if (dev->sys == USB) {
		if (dev->claim_interfaces_by(dev, 3, 0, 0) <= 0) {
			LERROR("Failed to claim interfaces");
			goto hotplug_cb_fail;
		}
	}
	//TODO fix serial grabbing
	if (!read_serial(sc)) {
		LERROR("Failed to read serial number");
		goto hotplug_cb_failed_to_configure;
	}
	//TODO needed?
	if (!clear_mappings(sc))
		// clear_mappings is needed on Windows, as kernel driver cannot be deatached there
		goto hotplug_cb_failed_to_configure;
	if (!configure(sc))
		goto hotplug_cb_failed_to_configure;
	if (!dev->interupt_read_loop(dev, ENDPOINT, PACKET_SIZE, &input_interrupt_cb, sc))
	DEBUG("New BLE Steam Controller with serial %s connected", sc->serial);
	sc->state = SS_READY;
	if (!daemon->controller_add(&sc->controller)) {
		// This shouldn't happen unless memory is running out
		DEBUG("Failed to add controller to daemon");
		goto hotplug_cb_fail;
	}
	return true;
hotplug_cb_failed_to_configure:
	LERROR("Failed to configure controlller");
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
	Subsystem s = HIDAPI;
#if defined(_WIN32)
	#define FILTERS &filter_vendor, &filter_product, &filter_idx
#elif defined(__BSD__)
	#define FILTERS &filter_vendor, &filter_product, &filter_idx
	s = UHID;
#else
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

