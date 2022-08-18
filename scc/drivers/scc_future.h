#pragma once
#include <stdint.h>

typedef struct ControllerInput ControllerInput;

typedef uint16_t Axis;
typedef uint16_t Keycode;

typedef uint8_t TriggerValue;
typedef int16_t AxisValue;
typedef int16_t GyroValue;

typedef enum SCButton {
	B_RPADTOUCH			= 0b000010000000000000000000000000000,
	B_LPADTOUCH			= 0b000001000000000000000000000000000,
	B_RPADPRESS			= 0b000000100000000000000000000000000,
	B_LPADPRESS			= 0b000000010000000000000000000000000,
	B_RGRIP				= 0b000000001000000000000000000000000,
	B_LGRIP				= 0b000000000100000000000000000000000,
	B_START				= 0b000000000010000000000000000000000,
	B_C					= 0b000000000001000000000000000000000,
	B_BACK				= 0b000000000000100000000000000000000,
	B_A					= 0b000000000000000001000000000000000,
	B_X					= 0b000000000000000000100000000000000,
	B_B					= 0b000000000000000000010000000000000,
	B_Y					= 0b000000000000000000001000000000000,
	B_LB				= 0b000000000000000000000100000000000,
	B_RB				= 0b000000000000000000000010000000000,
	B_LT				= 0b000000000000000000000001000000000,
	B_RT				= 0b000000000000000000000000100000000,
	// CPADTOUCH and CPADPRESS is used only on DS4 pad
	B_CPADTOUCH			= 0b000000000000000000000000000000100,
	B_CPADPRESS			= 0b000000000000000000000000000000010,
	B_STICKPRESS		= 0b001000000000000000000000000000000,
	B_RSTICKPRESS		= 0b010000000000000000000000000000000,
	// SteamDeck only buttons
	B_DOTS				= 0b000000000000000000000000000001000,
	B_RGRIP2			= 0b000000000000000000000000000100000,
	B_LGRIP2			= 0b000000000000000000000000000010000,
	_SCButton_padding = 0xFFFFFFFF	// uint32_t
} SCButton;

struct GyroInput {
	GyroValue			gpitch;
	GyroValue			groll;
	GyroValue			gyaw;
	GyroValue			q1;
	GyroValue			q2;
	GyroValue			q3;
	GyroValue			q4;
};

struct ControllerInput {
	SCButton				buttons;
	union {
		TriggerValue		triggers[2];
		struct {
			TriggerValue	ltrig;
			TriggerValue	rtrig;
		};
	};
	union {
		AxisValue			axes[12];
		struct {
			AxisValue		stick_x;
			AxisValue		stick_y;
			AxisValue		lpad_x;
			AxisValue		lpad_y;
			AxisValue		rpad_x;
			AxisValue		rpad_y;
			AxisValue		cpad_x;
			AxisValue		cpad_y;
			AxisValue		dpad_x;
			AxisValue		dpad_y;
			AxisValue		rstick_x;
			AxisValue		rstick_y;
		};
	};
	struct GyroInput		gyro;
};

typedef struct Mapper Mapper;
struct Mapper {
	void		(*input)(Mapper* m, ControllerInput* i);
};


#define STICK_PAD_MIN		((AxisValue)-0x8000)
#define STICK_PAD_MAX		((AxisValue) 0x7FFF)
#define STICK_PAD_MIN_HALF	((AxisValue)-0x4000)
#define STICK_PAD_MAX_HALF	((AxisValue) 0x3FFF)

#define TRIGGER_MIN			((TriggerValue)0)
#define TRIGGER_HALF		((TriggerValue)50)
// TRIGGER_CLICK is value on which trigger clicks
#define TRIGGER_CLICK		((TriggerValue)254)
#define TRIGGER_MAX			((TriggerValue)255)
#define NO_AXIS				((Axis)(REL_MAX + 1))
