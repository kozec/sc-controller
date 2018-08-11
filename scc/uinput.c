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
#include <sys/param.h>
#include <fcntl.h>
#include <linux/uinput.h>
#include <string.h>
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>
#include <unistd.h>

#pragma GCC diagnostic ignored "-Wunused-result"
#define UNPUT_MODULE_VERSION 9
#define MAX_FF_EVENTS 4

#define INFINITE_RUMBLE		10000		// Not really infinite, but longer than controller can handle

struct feedback_effect {
	bool in_use;
	bool continuous_rumble;
	int32_t duration;
	int32_t delay;
	int32_t repetitions;
	uint16_t type;
	int16_t level;
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
	__u16   version,
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
	uidev.id.version = version;
	uidev.ff_effects_max = 1;

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
		return -4;
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
		if (ioctl (fd, UI_SET_EVBIT, EV_FF) < 0) return -13;
		if (ioctl (fd, UI_SET_FFBIT, FF_RUMBLE) < 0) return -13;
		if (ioctl (fd, UI_SET_FFBIT, FF_PERIODIC) < 0) return -13;
		if (ioctl (fd, UI_SET_FFBIT, FF_SQUARE) < 0) return -13;
		if (ioctl (fd, UI_SET_FFBIT, FF_TRIANGLE) < 0) return -13;
		if (ioctl (fd, UI_SET_FFBIT, FF_SINE) < 0) return -13;
		if (ioctl (fd, UI_SET_FFBIT, FF_GAIN) < 0) return -13;
		
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

const int uinput_module_version(void) {
	return UNPUT_MODULE_VERSION;
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

// #define RUMBLE_DEBUG(...) do { printf(__VA_ARGS__); } while (0)
#define RUMBLE_DEBUG(...) do { } while (0)

int uinput_ff_read(int fd, int ff_effects_max, struct feedback_effect** ff_effects) {
	static struct uinput_ff_upload upload;
	static struct uinput_ff_erase erase;
	static struct input_event event;
	int n = read(fd, &event, sizeof(event));
	int rv = -1;
	int eid;
	if (n == sizeof(struct input_event)) {
		switch (event.type) {
			case EV_UINPUT:
				switch (event.code) {
					case UI_FF_UPLOAD:
						memset(&upload, 0, sizeof(struct uinput_ff_upload));
						upload.request_id = event.value;
						ioctl(fd, UI_BEGIN_FF_UPLOAD, &upload);
						
						upload.effect.id = -1;
						if ((upload.old.type != 0) && (upload.old.id >= 0) && (upload.old.id < ff_effects_max) && (ff_effects[upload.old.id]->in_use)) {
							// Updating old effect
							eid = upload.effect.id = upload.old.id;
							ff_effects[eid]->in_use = true;
							RUMBLE_DEBUG("Updated effect id %i\n", upload.effect.id);
						} else if (upload.old.type == 0) {
							// Generating new effect
							for (eid=0; eid<ff_effects_max; eid++) {
								if (!ff_effects[eid]->in_use) {
									ff_effects[eid]->in_use = true;
									upload.effect.id = eid;
									RUMBLE_DEBUG("Generated new effect id %i\n", upload.effect.id);
									break;
								}
							}
						}
						
						if (upload.effect.id >= 0) {
							int32_t avg;
							eid = upload.effect.id;
							ff_effects[eid]->duration = upload.effect.replay.length;
							ff_effects[eid]->delay = upload.effect.replay.delay;
							ff_effects[eid]->repetitions = 0;
							ff_effects[eid]->type = upload.effect.type;
							ff_effects[eid]->level = 0x4FFF;
							// This part converts all possible event types to one that
							// SCC and controller really supports. Only output level is used.
							switch (upload.effect.type) {
								case FF_CONSTANT:
									ff_effects[eid]->level = upload.effect.u.constant.level;
									RUMBLE_DEBUG("FF_CONSTANT [%i] %i\n", eid, ff_effects[eid]->level);
									break;
								case FF_PERIODIC:
									RUMBLE_DEBUG("FF_PERIODIC [%i] %i %i %i %i %i length %i\n",
										eid,
										upload.effect.u.periodic.waveform,
										upload.effect.u.periodic.period,
										upload.effect.u.periodic.magnitude,
										upload.effect.u.periodic.offset,
										upload.effect.u.periodic.phase,
										ff_effects[eid]->duration
									);
									ff_effects[eid]->level = upload.effect.u.periodic.magnitude;
									break;
								case FF_RAMP:
									ff_effects[eid]->level = upload.effect.u.ramp.start_level;
									RUMBLE_DEBUG("FF_RAMP [%i] %i\n", eid, ff_effects[eid]->level);
									break;
								case FF_RUMBLE:
									RUMBLE_DEBUG("FF_RUMBLE [%i] %i %i\n",
										eid,
										upload.effect.u.rumble.strong_magnitude,
										upload.effect.u.rumble.weak_magnitude
									);
									avg = upload.effect.u.rumble.strong_magnitude / 3 +
										upload.effect.u.rumble.weak_magnitude / 6;
									ff_effects[eid]->level = (int32_t)MIN(avg, 0x7FFF);
									if (ff_effects[eid]->continuous_rumble) {
										// See comment in case EV_FF: block
										ff_effects[eid]->duration = INFINITE_RUMBLE;
										ff_effects[eid]->repetitions = 1;
										rv = eid;
										RUMBLE_DEBUG("FF_PLAY_RUMBLE -> %i\n", eid);
									}
									break;
								case FF_FRICTION:
									RUMBLE_DEBUG("FF_FRICTION [%i] \n", eid);
									ff_effects[eid]->level = 0x7FFF;
									break;
								case FF_DAMPER:
									RUMBLE_DEBUG("FF_DAMPER [%i] \n", eid);
									ff_effects[eid]->level = 0x7FFF;
									break;
								case FF_INERTIA:
									RUMBLE_DEBUG("FF_INERTIA [%i] \n", eid);
									ff_effects[eid]->level = 0x7FFF;
									break;
								case FF_SPRING:
									RUMBLE_DEBUG("FF_SPRING [%i] \n", eid);
									ff_effects[eid]->level = 0x7FFF;
									break;
								case FF_CUSTOM:
									RUMBLE_DEBUG("FF_CUSTOM [%i] \n", eid);
									ff_effects[eid]->level = 0x7FFF;
									break;
							}
							
							upload.retval = 0;
						} else {
							// Upload failed
							RUMBLE_DEBUG("Cannot create more effects!\n");
							upload.retval = -1;
						}
						
						ioctl(fd, UI_END_FF_UPLOAD, &upload);
						break;
					case UI_FF_ERASE:
						memset(&erase, 0, sizeof(struct uinput_ff_erase));
						erase.request_id = event.value;
						ioctl(fd, UI_BEGIN_FF_ERASE, &erase);
						if ((erase.effect_id >= 0) && (erase.effect_id < ff_effects_max)) {
							ff_effects[erase.effect_id]->in_use = false;
						}
						RUMBLE_DEBUG("Erased effect id %i\n", upload.effect.id);
						ioctl(fd, UI_END_FF_ERASE, &erase);
						break;
					default:
						break;
				}
				break;
			case EV_FF:
				switch (event.code) {
					case FF_GAIN:
						RUMBLE_DEBUG("FF_GAIN\n");
						break;
					case FF_AUTOCENTER:
						// TODO: Maybe support theese?
						RUMBLE_DEBUG("FF_AUTOCENTER\n");
						break;
					default:
						if ((event.code >= 0) && (event.code < ff_effects_max)) {
							if (ff_effects[event.code]->in_use) {
								rv = event.code;
								ff_effects[rv]->repetitions = event.value;
								if ( (ff_effects[rv]->type == FF_RUMBLE) && (ff_effects[rv]->duration == 0) ) {
									// With FF_RUMBLE, duration of zero means infinite duration
									ff_effects[rv]->duration = INFINITE_RUMBLE;
								}
								if ( (ff_effects[rv]->type == FF_RUMBLE) && (event.value > 0) && ( (ff_effects[rv]->duration >= INFINITE_RUMBLE) || (event.value > 1) )) {
									// continuous_rumble is special kind of effect used by some games.
									// This event is "played" infinitelly, but with zero amplitide and whenever actual rumble is
									// supposed to play, effect properties are updated on the fly.
									if (!ff_effects[rv]->continuous_rumble) {
										ff_effects[rv]->continuous_rumble = true;
										RUMBLE_DEBUG("CONTINUOUS RUMBLE enabled on %i\n", rv);
									}
								} else if (ff_effects[rv]->continuous_rumble) {
									RUMBLE_DEBUG("CONTINUOUS RUMBLE disabled on %i\n", rv);
									ff_effects[rv]->continuous_rumble = false;
								}
								RUMBLE_DEBUG("FF_PLAY -> %i (type %i, lvl %i, dur. %i, reps. %i)\n", event.code,
									ff_effects[rv]->type, ff_effects[rv]->level, ff_effects[rv]->duration,
									ff_effects[rv]->repetitions, event.value);
							} else {
								// SDL uses this to turn rumble off - fake event
								// is generated here to achieve same effect
								rv = event.code;
								ff_effects[rv]->level = 0;
								ff_effects[rv]->repetitions = 0;
								ff_effects[rv]->duration = 0;
								RUMBLE_DEBUG("FF NOT IN USE! %i\n", event.code);
							}
						}
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
