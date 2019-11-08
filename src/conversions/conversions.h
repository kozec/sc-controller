#pragma once
#include <stdint.h>

struct Item {
	uint16_t			value;
	const char*			name;
	uint32_t			hw_scan;
	uint16_t 			x11_keycode;
	uint16_t			win32_scan;
	uint8_t				win32_vk;
};

