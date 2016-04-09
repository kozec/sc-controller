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
#include <unistd.h>

int uinput_init(
    int     key_len,
    __u16 * key,
    int     abs_len,
    __u16 * abs,
    __s32 * abs_min,
    __s32 * abs_max,
    __s32 * abs_fuzz,
    __s32 * abs_flat,
    int     rel_len,
    __u16 * rel,
    int     keyboard,
    __u16   vendor,
    __u16   product,
    char *  name)
{
    struct uinput_user_dev uidev;
    int fd;
    int i;

    memset(&uidev, 0, sizeof(uidev));

    fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
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

void uinput_destroy(int fd)
{
    ioctl(fd, UI_DEV_DESTROY);
    close(fd);
}
