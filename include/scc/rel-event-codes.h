/**
 * This file overrides REL_x event codes.
 * Override is needed, as originally REL_X == ABS_X == 0, what makes converting
 * back from "0" impossible.
 */
#ifndef _REL_EVENT_CODES_H
#define _REL_EVENT_CODES_H

#ifndef ABS_X
#error "Please, include input-event-codes.h first"
#endif

#define SCC_REL_OFFSET 1024

#undef REL_X
#undef REL_Y
#undef REL_Z
#undef REL_RX
#undef REL_RY
#undef REL_RZ
#undef REL_HWHEEL
#undef REL_DIAL
#undef REL_WHEEL
#undef REL_MISC
#undef REL_MAX
#undef REL_CNT

#define REL_X			(SCC_REL_OFFSET + 0x00)
#define REL_Y			(SCC_REL_OFFSET + 0x01)
#define REL_Z			(SCC_REL_OFFSET + 0x02)
#define REL_RX			(SCC_REL_OFFSET + 0x03)
#define REL_RY			(SCC_REL_OFFSET + 0x04)
#define REL_RZ			(SCC_REL_OFFSET + 0x05)
#define REL_HWHEEL		(SCC_REL_OFFSET + 0x06)
#define REL_DIAL		(SCC_REL_OFFSET + 0x07)
#define REL_WHEEL		(SCC_REL_OFFSET + 0x08)
#define REL_MISC		(SCC_REL_OFFSET + 0x09)
#define REL_MAX			(SCC_REL_OFFSET + 0x0f)
#define REL_CNT			(REL_MAX - REL_X + 1)

#endif

