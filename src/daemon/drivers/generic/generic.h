#ifdef __linux__
#define LOG_TAG "udev_drv"
#else
#define LOG_TAG "gnrc_drv"
#endif

#include "scc/utils/logging.h"
#include "scc/utils/intmap.h"
#include "scc/utils/aojls.h"
#include "scc/driver.h"
#include <stddef.h>
#include <unistd.h>

#define MAX_DESC_LEN	64
#define MAX_ID_LEN		32


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


/**
 * Axis map is map int -> AxisData
 * Returns NULL if memory cannot be allocated
 */
intmap_t axis_map_new();

void axis_map_free(intmap_t map);

/**
 * Loads and parses button map from given JSON object.
 * Updates 'button_map' in place.
 *
 * Returns false on failure, which can be caused only by OOM error
 */
bool load_button_map(const char* name, json_object* json, intmap_t button_map);

/**
 * Loads and parses axis map from given JSON object.
 * Updates 'axis_map' in place.
 *
 * Returns false on failure, which can be caused only by OOM error
 */
bool load_axis_map(const char* name, json_object* json, intmap_t axis_map);

/**
 * Applies input_value, as read from physical controller, to ControllerInput
 * of virtual controller.
 */
void apply_axis(const AxisData* a, double input_value, ControllerInput* input);

/**
 * Generates controller ID using 'base' as prefix and stores it to target.
 * 'counter' should be 0, unless function is called repeadedly because returned
 * ID was not unique.
 * Target has to have space for at least MAX_ID_LEN bytes (including terminating \0)
 */
void make_id(const char* base, char target[MAX_ID_LEN], int counter);

