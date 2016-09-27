/*
 * The MIT License (MIT)
 *
 * Copyright (c) 2015 Stany MARCEL <stanypub@gmail.com>
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <linux/uinput.h>
#include <string.h>
#include <stdbool.h>
#include <unistd.h>

#pragma GCC diagnostic ignored "-Wunused-result"
#define MAX_FF_EVENTS 4

struct feedback_effect {
	bool in_use;
	bool forever;
	bool playing;
	int32_t duration;
	int32_t delay;
	int32_t repetitions;
	struct timespec start_time;
	struct timespec end_time;
};

int uinput_init(
	int	 key_len,
	__u16 * key,
	int	 abs_len,
	__u16 * abs,
	__s32 * abs_min,
	__s32 * abs_max,
	__s32 * abs_fuzz,
	__s32 * abs_flat,
	int	 rel_len,
	__u16 * rel,
	int	 keyboard,
	__u16   vendor,
	__u16   product,
	int	ff_effects_max,
	char *  name)
{
	struct uinput_user_dev uidev;
	int fd;
	int i;

	memset(&uidev, 0, sizeof(uidev));
	
	int mode = O_WRONLY | O_NONBLOCK;
	if (ff_effects_max > 0)
		mode = O_RDWR | O_NONBLOCK;
	fd = open("/dev/uinput", mode);
	if (fd < 0)
		return -1;

	strncpy(uidev.name, name, UINPUT_MAX_NAME_SIZE);
	uidev.id.bustype = BUS_USB;
	uidev.id.vendor = vendor;
	uidev.id.product = product;
	uidev.id.version = 1;

	/* Key Event initialisation */
	if (key_len > 0 && ioctl(fd, UI_SET_EVBIT, EV_KEY) < 0) {
		close(fd);
		return -2;
	}

	for (i = 0; i < key_len; i++) {
		if (ioctl(fd, UI_SET_KEYBIT, key[i]) < 0) {
			close(fd);
			return -3;
		}
	}

	/* Absolute Event initialisation */
	if (abs_len > 0 && ioctl(fd, UI_SET_EVBIT, EV_ABS) < 0) {
		close(fd);
		return -4;;
	}

	for (i = 0; i < abs_len; i++) {

		if (ioctl(fd, UI_SET_ABSBIT, abs[i]) < 0) {
			close(fd);
			return -5;
		}
		uidev.absmin[abs[i]] = abs_min[i];
		uidev.absmax[abs[i]] = abs_max[i];
		uidev.absfuzz[abs[i]] = abs_fuzz[i];
		uidev.absflat[abs[i]] = abs_flat[i];
	}

	/* Relative Event initialisation */
	if (rel_len > 0 && ioctl(fd, UI_SET_EVBIT, EV_REL) < 0) {
		close(fd);
		return -6;
	}

	for (i = 0; i < rel_len; i++) {
		if (ioctl(fd, UI_SET_RELBIT, rel[i]) < 0) {
			close(fd);
			return -7;
		}
	}

	if (keyboard) {
		if (ioctl(fd, UI_SET_EVBIT, EV_MSC) < 0) {
			close(fd);
			return -8;
		}
		if (ioctl(fd, UI_SET_MSCBIT, MSC_SCAN) < 0) {
			close(fd);
			return -9;
		}
		if (ioctl(fd, UI_SET_EVBIT,  EV_REP) < 0) {
			close(fd);
			return -10;
		}
	}
	
	/* rumble initialisation */
	if (ff_effects_max > 0) {
		if (ioctl(fd, UI_SET_EVBIT, EV_FF) < 0)
			return -13;
		
		if (ioctl(fd, UI_SET_FFBIT, FF_RUMBLE) < 0)
			return -14;
		
		uidev.ff_effects_max = ff_effects_max;
	}

	/* submit the uidev */
	if (write(fd, &uidev, sizeof(uidev)) < 0) {
		close(fd);
		return -11;
	}

	/* create the device */
	if (ioctl(fd, UI_DEV_CREATE) < 0) {
		close(fd);
		return -12;
	}

	return fd;
}

const int uinput_module_version() {
	return 2;
}

void uinput_key(int fd, __u16 key, __s32 val)
{
	struct input_event ev;

	memset(&ev, 0, sizeof(ev));
	ev.type = EV_KEY;
	ev.code = key;
	ev.value = val;
	write(fd, &ev, sizeof(ev));
}

void uinput_abs(int fd, __u16 abs, __s32 val)
{
	struct input_event ev;

	memset(&ev, 0, sizeof(ev));
	ev.type = EV_ABS;
	ev.code = abs;
	ev.value = val;
	write(fd, &ev, sizeof(ev));
}

void uinput_rel(int fd, __u16 rel, __s32 val)
{
	struct input_event ev;

	memset(&ev, 0, sizeof(ev));
	ev.type = EV_REL;
	ev.code = rel;
	ev.value = val;
	write(fd, &ev, sizeof(ev));
}

void uinput_scan(int fd, __s32 val)
{
	struct input_event ev;

	memset(&ev, 0, sizeof(ev));
	ev.type = EV_MSC;
	ev.code = MSC_SCAN;
	ev.value = val;
	write(fd, &ev, sizeof(ev));
}

void uinput_set_delay_period(int fd, __s32 delay, __s32 period)
{
	struct input_event ev;

	memset(&ev, 0, sizeof(ev));
	ev.type = EV_REP;
	ev.code = REP_DELAY;
	ev.value = delay;
	write(fd, &ev, sizeof(ev));
	ev.code = REP_PERIOD;
	ev.value = period;
	write(fd, &ev, sizeof(ev));
}

void uinput_syn(int fd)
{
	struct input_event ev;

	memset(&ev, 0, sizeof(ev));
	ev.type = EV_SYN;
	ev.code = SYN_REPORT;
	ev.value = 0;
	write(fd, &ev, sizeof(ev));
}


int uinput_ff_read(int fd, int ff_effects_max, struct feedback_effect** ff_effects) {
	static struct uinput_ff_upload upload = { 0 };
	static struct uinput_ff_erase erase = { 0 };
	static struct input_event event;
	int n = read(fd, &event, sizeof(event));
	int rv = -1;
	int i;
	if (n == sizeof(struct input_event)) {
		switch (event.type) {
			case EV_UINPUT:
				switch (event.code) {
					case UI_FF_UPLOAD:
						upload.request_id = event.value;
						ioctl(fd, UI_BEGIN_FF_UPLOAD, &upload);
						upload.retval = -1;
						if (upload.old.type != 0) {
							// Updating old effect
							upload.retval = 0;
							rv = upload.effect.id = upload.old.id;
							ff_effects[rv]->in_use = true;
						} else {
							// Generating new effect
							for (i=0; i<ff_effects_max; i++) {
								if (!ff_effects[i]->in_use) {
									ff_effects[i]->in_use = true;
									upload.retval = 0;
									rv = upload.effect.id = i;
									break;
								}
							}
						}
						if (rv >= 0) {
							ff_effects[rv]->forever = (upload.effect.replay.length == 0);
							ff_effects[rv]->duration = upload.effect.replay.length;
							ff_effects[rv]->delay = upload.effect.replay.delay;
							ff_effects[rv]->repetitions = 0;
						}
						ioctl(fd, UI_END_FF_UPLOAD, &upload);
						break;
					case UI_FF_ERASE:
						erase.request_id = event.value;
						ioctl(fd, UI_BEGIN_FF_ERASE, &erase);
						if ((erase.effect_id >= 0) && (erase.effect_id < ff_effects_max)) {
							ff_effects[erase.effect_id]->in_use = false;
							rv = erase.effect_id;
						}
						ioctl(fd, UI_END_FF_ERASE, &erase);
						break;
					default:
						break;
				}
			case EV_FF:
				if ((event.code >= 0) && (event.code < ff_effects_max) && (ff_effects[event.code]->in_use)) {
					rv = event.code;
					ff_effects[rv]->repetitions = event.value;
				}
				break;
			default:
				break;
		}
	}
	return rv;
}

void uinput_destroy(int fd)
{
	ioctl(fd, UI_DEV_DESTROY);
	close(fd);
}
