#ifdef __linux__
#define LOG_TAG "evdev_drv"
#else
#define LOG_TAG "gnrc_drv"
#endif

#include "scc/utils/logging.h"
#include "scc/utils/intmap.h"
#include "scc/utils/aojls.h"
#include "scc/config.h"
#include "scc/driver.h"
#include <stddef.h>
#include <unistd.h>

#define MAX_DESC_LEN				64
#define MAX_ID_LEN					64
#define PADPRESS_EMULATION_TIMEOUT	2		/* ms */
#define C_EMULATION_TIMEOUT			100		/* ms */

/**
 * Mix-in for stuff that's common for all (two) generic drivers
 * Note that it's important for this to be 2nd field of parent structure,
 * so get_gc_from_controller_instance() method works.
 */
typedef struct GenericController {
	Mapper*					mapper;
	Daemon*					daemon;
	intmap_t				button_map;
	/** largest key in button_map */
	intptr_t				button_max;
	/** int -> AxisData */
	intmap_t				axis_map;
	bool					emulate_c;
	TaskID					emulate_c_task;
	SCButton				held_buttons;
	ControllerInput			input;
	char					id[MAX_ID_LEN];
	char					desc[MAX_DESC_LEN];
	TaskID					padpressemu_task;
} GenericController;



typedef enum AxisID {
	A_NONE		= -1,
	A_STICK_X	= 0x00,
	A_STICK_Y	= 0x01,
	A_LPAD_X	= 0x02,
	A_LPAD_Y	= 0x03,
	A_RPAD_X	= 0x04,
	A_RPAD_Y	= 0x05,
	A_CPAD_X	= 0x06,
	A_CPAD_Y	= 0x07,
	A_LTRIG		= 0x10,
	A_RTRIG		= 0x11,
} AxisID;


typedef struct AxisData {
	AxisID					axis;
	double					scale;
	double					offset;
	double					deadzone;
	int32_t					center;
	int32_t					clamp_min;
	int32_t					clamp_max;
} AxisData;


/** Sets up and allocates fields in GenericController structure */
bool gc_alloc(Daemon* d, GenericController* gc);
/** Deallocates fields in GenericController structure (but not structure itself) */
void gc_dealloc(GenericController* gc);
/** Callback used when emulating pressing left pad */
void gc_cancel_padpress_emulation(void* _gc);
/**
 * Generates unique controller ID using 'base' as prefix.
 */
void gc_make_id(const char* base, GenericController* gc);

/** Controller.get_id callback */
const char* gc_get_id(Controller* c);
/** Controller.get_description callback */
const char* gc_get_description(Controller* c);
/** Controller.set_mapper callback */
void gc_set_mapper(Controller* c, Mapper* mapper);
/** Controller.turnoff callback */
void gc_turnoff(Controller* c);

/** Loads mappings from provided config object */
bool gc_load_mappings(GenericController* gc, Config* ccfg);

/**
 * Applies input_value, as read from physical controller, to ControllerInput
 * of virtual controller.
 */
bool apply_axis(GenericController* gc, uintptr_t code, double value);

/** Same as 'apply_axis', applies button */
bool apply_button(Daemon* d, GenericController* gc, uintptr_t code, uint8_t value);

