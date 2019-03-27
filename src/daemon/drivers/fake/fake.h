/**
 * SC Controller - fake gamepad driver
 *
 * Fake physical gamepad used for testing. Set SCC_FAKES=1 (or larger) to enable.
 */
#include "scc/driver.h"
#include "scc/mapper.h"

/** MAX_DESC_LEN has to fit "<FakeGamepad #99>" */
#define MAX_DESC_LEN	32
#define MAX_ID_LEN		24

typedef struct FakeGamepad {
	Controller				controller;
	Mapper*					mapper;
	char					desc[MAX_DESC_LEN];
	char					id[MAX_ID_LEN];
} FakeGamepad;


FakeGamepad* fakegamepad_new();

