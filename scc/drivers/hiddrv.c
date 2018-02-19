#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <inttypes.h>
#include <stdbool.h>
#include <limits.h>
#define CLAMP(min, x, max) x

#define HIDDRV_MODULE_VERSION 5
PyObject* module;

#define AXIS_COUNT 17
#define BUTTON_COUNT 32

struct HIDControllerInput {
	uint32_t buttons;
	int32_t axes[AXIS_COUNT];
};


enum AxisType {
	AXIS_LPAD_X  = 0,
	AXIS_LPAD_Y  = 1,
	AXIS_RPAD_X  = 2,
	AXIS_RPAD_Y  = 3,
	AXIS_STICK_X = 4,
	AXIS_STICK_Y = 5,
	AXIS_LTRIG   = 6,
	AXIS_RTRIG   = 7,
	AXIS_GPITCH  = 8,
	AXIS_GROLL   = 9,
	AXIS_GYAW    = 10,
	AXIS_Q1      = 11,
	AXIS_Q2      = 12,
	AXIS_Q3      = 13,
	AXIS_Q4      = 14,
	AXIS_CPAD_X  = 15,
	AXIS_CPAD_Y  = 16,
	_AxisType_force_int = INT_MAX
};


enum AxisMode {
	DISABLED      = 0,
	AXIS          = 1,
	AXIS_NO_SCALE = 2,
	DPAD          = 3,
	HATSWITCH     = 4,
	DS4ACCEL      = 5,
	DS4GYRO       = 6,
	DS4TOUCHPAD   = 7,
	_AxisMode_force_int = INT_MAX
};


struct AxisModeData {
	uint32_t button;
	float scale;
	float offset;
	int clamp_min;
	int clamp_max;
	float deadzone;
};


struct DPadModeData {
	uint32_t button;
	unsigned char button1;
	unsigned char button2;
	int min;
	int max;
};


struct HatswitchModeData {
	uint32_t button;
	int min;
	int max;
};


union AxisDataUnion {
	struct AxisModeData axis;
	struct DPadModeData dpad;
	struct HatswitchModeData hatswitch;
};


struct AxisData {
	enum AxisMode mode;
	size_t byte_offset;
	uint8_t bit_offset;
	uint8_t size;
	
	union AxisDataUnion data;
};


struct ButtonData {
	bool enabled;
	size_t byte_offset;
	uint8_t bit_offset;
	uint8_t size;
	uint8_t button_count;
	uint8_t button_map[BUTTON_COUNT];
};


struct HIDDecoder {
	struct AxisData axes[AXIS_COUNT];
	struct ButtonData buttons;
	size_t packet_size;
	
	struct HIDControllerInput old_state;
	struct HIDControllerInput state;
};


union Value {
	uint8_t  u8;
	uint16_t u16;
	int16_t  s16;
	uint32_t u32;
	uint64_t u64;
};


static union Value grab_value(const char* data, const size_t byte_offset, uint8_t bit_offset) {
	union Value val = *((union Value*)(data + byte_offset));
	val.u64 = val.u64 >> bit_offset;
	return val;
}


static int grab_with_size(const uint8_t size, const char* data, const size_t byte_offset, uint8_t bit_offset) {
	union Value val = grab_value(data, byte_offset, bit_offset);
	// if (size == 16)
	// 	printf(" => %i\n", (int)val.u16);
	switch (size) {
		case 16: return val.u16;
		case 32: return val.u32;
		case 64: return val.u64;
		default: return val.u8;
	}
}


bool decode(struct HIDDecoder* dec, const char* data) {
	size_t i;
	memcpy(&(dec->old_state), &(dec->state), sizeof(struct HIDControllerInput));
	dec->state.buttons = 0;
	// Axes
	for (i=0; i<AXIS_COUNT; i++) {
		union Value value;
		float fval;
		switch (dec->axes[i].mode) {
			case AXIS:
				fval = ((grab_with_size(dec->axes[i].size,
						data, dec->axes[i].byte_offset, dec->axes[i].bit_offset)
							* dec->axes[i].data.axis.scale)
							+ dec->axes[i].data.axis.offset
				);
				if ((fval >= -dec->axes[i].data.axis.deadzone) && (fval <= dec->axes[i].data.axis.deadzone)) {
						dec->state.axes[i] = 0;
				} else {
					dec->state.buttons |= dec->axes[i].data.dpad.button;
					dec->state.axes[i] = CLAMP(
		 				dec->axes[i].data.axis.clamp_min,
		 				fval * dec->axes[i].data.axis.clamp_max,
		 				dec->axes[i].data.axis.clamp_max
					);
				}
				break;
			case AXIS_NO_SCALE:
				dec->state.axes[i] = grab_with_size(dec->axes[i].size,
					data, dec->axes[i].byte_offset, dec->axes[i].bit_offset);
				break;
			case DPAD:
				value = grab_value(data, dec->axes[i].byte_offset,
					dec->axes[i].bit_offset);
				if ((value.u32 >> dec->axes[i].data.dpad.button1) & 1) {
					dec->state.buttons |= dec->axes[i].data.dpad.button;
					dec->state.axes[i] = dec->axes[i].data.dpad.min;
				} else if ((value.u32 >> dec->axes[i].data.dpad.button2) & 1) {
					dec->state.buttons |= dec->axes[i].data.dpad.button;
					dec->state.axes[i] = dec->axes[i].data.dpad.max;
				}
				break;
			case HATSWITCH:
				value = grab_value(data, dec->axes[i].byte_offset,
					dec->axes[i].bit_offset);
				switch (value.u8 & 0b1111) {
					case 0:	// up
						dec->state.axes[i + 0] = 0;
						dec->state.axes[i + 1] = dec->axes[i].data.hatswitch.max;
						dec->state.buttons |= dec->axes[i].data.hatswitch.button;
						break;
					case 1:	// up-right
						dec->state.axes[i + 0] = dec->axes[i].data.hatswitch.max;
						dec->state.axes[i + 1] = dec->axes[i].data.hatswitch.max;
						dec->state.buttons |= dec->axes[i].data.hatswitch.button;
						break;
					case 2:	// right
						dec->state.axes[i + 0] = dec->axes[i].data.hatswitch.max;
						dec->state.axes[i + 1] = 0;
						dec->state.buttons |= dec->axes[i].data.hatswitch.button;
						break;
					case 3:	// down-right
						dec->state.axes[i + 0] = dec->axes[i].data.hatswitch.max;
						dec->state.axes[i + 1] = dec->axes[i].data.hatswitch.min;
						dec->state.buttons |= dec->axes[i].data.hatswitch.button;
						break;
					case 4:	// down
						dec->state.axes[i + 0] = 0;
						dec->state.axes[i + 1] = dec->axes[i].data.hatswitch.min;
						dec->state.buttons |= dec->axes[i].data.hatswitch.button;
						break;
					case 5:	// up-left
						dec->state.axes[i + 0] = dec->axes[i].data.hatswitch.min;
						dec->state.axes[i + 1] = dec->axes[i].data.hatswitch.min;
						dec->state.buttons |= dec->axes[i].data.hatswitch.button;
						break;
					case 6:	// left
						dec->state.axes[i + 0] = dec->axes[i].data.hatswitch.min;
						dec->state.axes[i + 1] = 0;
						dec->state.buttons |= dec->axes[i].data.hatswitch.button;
						break;
					case 7:	// down-left
						dec->state.axes[i + 0] = dec->axes[i].data.hatswitch.min;
						dec->state.axes[i + 1] = dec->axes[i].data.hatswitch.max;
						dec->state.buttons |= dec->axes[i].data.hatswitch.button;
						break;
					default: // centered
						dec->state.axes[i + 0] = 0;
						dec->state.axes[i + 1] = 0;
						break;
				}
				break;
			case DS4ACCEL:
				value = grab_value(data, dec->axes[i].byte_offset,
					dec->axes[i].bit_offset);
				dec->state.axes[i] = value.s16;
				break;
			case DS4GYRO:
				value = grab_value(data, dec->axes[i].byte_offset,
					dec->axes[i].bit_offset);
				dec->state.axes[i] = -value.s16;
				break;
			case DS4TOUCHPAD:
				value = grab_value(data, dec->axes[i].byte_offset,
					dec->axes[i].bit_offset);
				dec->state.axes[i] = (value.u16 & 0x0FFF);
				break;
			default:
				break;
		}
	}
	
	// Buttons
	if (dec->buttons.enabled) {
		union Value value = grab_value(data, dec->buttons.byte_offset, dec->buttons.bit_offset);
		for (i=0; i<BUTTON_COUNT; i++) {
			if (dec->buttons.button_map[i] < 33) {
				uint32_t bit = (value.u32 >> i) & 1;
				dec->state.buttons |= bit << dec->buttons.button_map[i];
			}
		}
	}
	return memcmp(&(dec->old_state), &(dec->state), sizeof(struct HIDControllerInput)) != 0;
}


const int hiddrv_module_version(void) {
	return HIDDRV_MODULE_VERSION;
}
