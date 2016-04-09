#!/usr/bin/env python

# The MIT License (MIT)
#
# Copyright (c) 2015 Stany MARCEL <stanypub@gmail.com>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""Event mapper class and enums used to map steamcontroller inputs to uinput
events

"""

from math import sqrt

from enum import IntEnum

from steamcontroller import \
    SCStatus, \
    SCButtons, \
    SCI_NULL

import steamcontroller.uinput as sui

from collections import deque

class Pos(IntEnum):
    """Specify witch pad or trig is used"""
    RIGHT = 0
    LEFT = 1

class Modes(IntEnum):
    """Different kinds of uinput event type"""
    GAMEPAD = 0
    KEYBOARD = 1
    MOUSE = 2
    CALLBACK = 3

class PadModes(IntEnum):
    """Different possible pads modes"""
    NOACTION = 0
    AXIS = 1
    MOUSE = 2
    MOUSESCROLL = 3
    BUTTONTOUCH = 4
    BUTTONCLICK = 5

class TrigModes(IntEnum):
    """Different possible trig modes"""
    NOACTION = 0
    AXIS = 1
    BUTTON = 2

class StickModes(IntEnum):
    """Different possible stick modes"""
    NOACTION = 0
    AXIS = 1
    BUTTON = 2

class EventMapper(object):
    """
    Event mapper class permit to configure events and provide the process event
    callback to be registered to a SteamController instance
    """

    def __init__(self):

        self._uip = (sui.Gamepad(),
                     sui.Keyboard(),
                     sui.Mouse())

        self._btn_map = {x : (None, 0) for x in list(SCButtons)}

        self._pad_modes = [PadModes.NOACTION, PadModes.NOACTION]
        self._pad_dzones = [0, 0]
        self._pad_evts = [[(None, 0)]*4]*2
        self._pad_revs = [False, False]

        self._trig_modes = [TrigModes.NOACTION, TrigModes.NOACTION]
        self._trig_evts = [(None, 0)]*2

        self._stick_mode = StickModes.NOACTION
        self._stick_evts = [(None, 0)]*2
        self._stick_rev = False

        self._sci_prev = SCI_NULL

        self._xdq = [deque(maxlen=8), deque(maxlen=8)]
        self._ydq = [deque(maxlen=8), deque(maxlen=8)]

        self._onkeys = set()
        self._onabs = {}

        self._stick_tys = None
        self._stick_lxs = None
        self._stick_bys = None
        self._stick_rxs = None
        self._stick_axes_callback = None
        self._stick_pressed_callback = None

        self._trig_s = [None, None]
        self._trig_axes_callbacks = [None, None]

        self._moved = [0, 0]


    def process(self, sc, sci):
        """
        Process SteamController inputs to generate events

        @param SteamController sc       steamcontroller class used to get input
        @param SteamControllerInput sci inputs from the steam controller
        """

        if sci.status != SCStatus.INPUT:
            return

        sci_p = self._sci_prev
        self._sci_prev = sci

        _xor = sci_p.buttons ^ sci.buttons
        btn_rem = _xor & sci_p.buttons
        btn_add = _xor & sci.buttons

        _pressed = []
        _released = []

        syn = set()

        def _abspressed(ev, val):
            if ev not in self._onabs or self._onabs[ev] != val:
                self._uip[Modes.GAMEPAD].axisEvent(ev, val)
                syn.add(Modes.GAMEPAD)
                self._onabs[ev] = val
                return True
            else:
                return False

        def _absreleased(ev):
            if ev not in self._onabs or self._onabs[ev] == 0:
                return False
            else:
                self._uip[Modes.GAMEPAD].axisEvent(ev, 0)
                syn.add(Modes.GAMEPAD)
                self._onabs[ev] = 0
                return True

        def _keypressed(mode, ev):
            """Private function used to generate different kind of key press"""
            if mode == Modes.GAMEPAD or mode == Modes.MOUSE:
                if ev not in self._onkeys:
                    self._uip[mode].keyEvent(ev, 1)
                    syn.add(mode)
            elif mode == Modes.KEYBOARD:
                _pressed.append(ev)
            if ev in self._onkeys:
                return False
            else:
                self._onkeys.add(ev)
                return True

        def _keyreleased(mode, ev):
            """Private function used to generate different kind of key release"""
            if ev in self._onkeys:
                self._onkeys.remove(ev)
                if mode == Modes.GAMEPAD or mode == Modes.MOUSE:
                    self._uip[mode].keyEvent(ev, 0)
                    syn.add(mode)
                elif mode == Modes.KEYBOARD:
                    _released.append(ev)
                return True
            else:
                return False

        # Manage buttons
        for btn, (mode, ev) in self._btn_map.items():

            if mode is None:
                continue
            if btn & btn_add:
                if mode is Modes.CALLBACK:
                    ev(self, btn, True)
                else:
                    _keypressed(mode, ev)
            elif btn & btn_rem:
                if mode is Modes.CALLBACK:
                    ev(self, btn, False)
                else:
                    _keyreleased(mode, ev)
        # Manage pads
        for pos in [Pos.LEFT, Pos.RIGHT]:

            if pos == Pos.LEFT:
                x, y = sci.lpad_x, sci.lpad_y
                x_p, y_p = sci_p.lpad_x, sci_p.lpad_y
                touch = SCButtons.LPADTOUCH
                click = SCButtons.LPAD
            else:
                x, y = sci.rpad_x, sci.rpad_y
                x_p, y_p = sci_p.rpad_x, sci_p.rpad_y
                touch = SCButtons.RPADTOUCH
                click = SCButtons.RPAD

            if sci.buttons & touch == touch:
                # Compute mean pos
                try:
                    xm_p = int(sum(self._xdq[pos]) / len(self._xdq[pos]))
                    ym_p = int(sum(self._ydq[pos]) / len(self._ydq[pos]))
                except ZeroDivisionError:
                    xm_p, ym_p = 0, 0
                self._xdq[pos].append(x)
                self._ydq[pos].append(y)
                try:
                    xm = int(sum(self._xdq[pos]) / len(self._xdq[pos]))
                    ym = int(sum(self._ydq[pos]) / len(self._ydq[pos]))
                except ZeroDivisionError:
                    xm, ym = 0, 0
                if not sci_p.buttons & touch == touch:
                    xm_p, ym_p = xm, ym


            # Mouse and mouse scroll modes
            if self._pad_modes[pos] in (PadModes.MOUSE, PadModes.MOUSESCROLL):
                _free = True
                _dx = 0
                _dy = 0

                if sci.buttons & touch == touch:
                    _free = False
                    if sci_p.buttons & touch == touch:
                        _dx = xm - xm_p
                        _dy = ym - ym_p

                if self._pad_modes[pos] == PadModes.MOUSE:
                    self._moved[pos] += int(self._uip[Modes.MOUSE].moveEvent(_dx, -_dy, _free))
                    # FIXME: make haptic configurable
                    if self._moved[pos] >= 4000:
                        if not _free:
                            sc.addFeedback(pos, amplitude=100)
                        self._moved[pos] %= 4000
                else:
                    if self._uip[Modes.MOUSE].scrollEvent(_dx, _dy, _free):
                        # FIXME: make haptic configurable
                        if not _free:
                            sc.addFeedback(pos, amplitude=256)


            # Axis mode
            elif self._pad_modes[pos] == PadModes.AXIS:
                revert = self._pad_revs[pos]
                (xmode, xev), (ymode, yev) = self._pad_evts[pos]
                if xmode is not None:

                    # FIXME: make haptic configurable
                    if sci.buttons & touch == touch:
                        self._moved[pos] += sqrt((xm - xm_p)**2 + (ym - ym_p)**2)
                        if self._moved[pos] >= 4000:
                            sc.addFeedback(pos, amplitude=100)
                            self._moved[pos] %= 4000

                    if x != x_p:
                        self._uip[xmode].axisEvent(xev, x)
                        syn.add(xmode)
                    if y != y_p:
                        self._uip[ymode].axisEvent(yev, y if not revert else -y)
                        syn.add(ymode)

            # Button touch mode
            elif (self._pad_modes[pos] == PadModes.BUTTONTOUCH or
                  self._pad_modes[pos] == PadModes.BUTTONCLICK):

                if self._pad_modes[pos] == PadModes.BUTTONTOUCH:
                    on_test = touch
                    off_test = touch
                else:
                    on_test = click | touch
                    off_test = click

                haptic = False

                if sci.buttons & on_test == on_test:
                    # get callback events
                    callbacks = []
                    for evt in self._pad_evts[pos]:
                        if evt[0] == Modes.CALLBACK:
                            callbacks.append(evt)
                    for callback_evt in callbacks:
                        callback_evt[1](self, pos, xm, ym)

                    dzone = self._pad_dzones[pos]
                    if len(self._pad_evts[pos]) == 4:
                        # key or buttons
                        tmode, tev = self._pad_evts[pos][0]
                        lmode, lev = self._pad_evts[pos][1]
                        bmode, bev = self._pad_evts[pos][2]
                        rmode, rev = self._pad_evts[pos][3]

                        if ym > dzone: # TOP
                            haptic |= _keypressed(tmode, tev)
                        else:
                            haptic |= _keyreleased(tmode, tev)

                        if xm < -dzone: # LEFT
                            haptic |= _keypressed(lmode, lev)
                        else:
                            haptic |= _keyreleased(lmode, lev)

                        if ym < -dzone: # BOTTOM
                            haptic |= _keypressed(bmode, bev)
                        else:
                            haptic |= _keyreleased(bmode, bev)

                        if xm > dzone: # RIGHT
                            haptic |= _keypressed(rmode, rev)
                        else:
                            haptic |= _keyreleased(rmode, rev)

                    elif len(self._pad_evts[pos]) == 2:
                        _, xev = self._pad_evts[pos][0]
                        _, yev = self._pad_evts[pos][1]
                        rev = self._pad_revs[pos]

                        if ym > dzone:    # TOP
                            haptic |= _abspressed(yev, -1 if rev else 1)
                        elif ym < -dzone: # BOTTOM
                            haptic |= _abspressed(yev, 1 if rev else -1)
                        else:
                            haptic |= _absreleased(yev)

                        if xm < -dzone:  # LEFT
                            haptic |= _abspressed(xev, -1)
                        elif xm > dzone: # RIGHT
                            haptic |= _abspressed(xev, 1)
                        else:
                            haptic |= _absreleased(xev)

                if (sci.buttons & off_test != off_test and
                    sci_p.buttons & on_test == on_test):
                    if len(self._pad_evts[pos]) == 4:
                        for mode, ev in self._pad_evts[pos]:
                            haptic |= _keyreleased(mode, ev)
                    elif len(self._pad_evts[pos]) == 2:
                        for _, ev in self._pad_evts[pos]:
                            haptic |= _absreleased(ev)

                if haptic and self._pad_modes[pos] == PadModes.BUTTONTOUCH:
                    sc.addFeedback(pos, amplitude=300)

            if sci.buttons & touch != touch:
                xm_p, ym_p, xm, ym = 0, 0, 0, 0
                self._xdq[pos].clear()
                self._ydq[pos].clear()


        # Manage Trig
        for pos in [Pos.LEFT, Pos.RIGHT]:
            trigval = sci.ltrig if pos == Pos.LEFT else sci.rtrig
            trigval_prev = sci_p.ltrig if pos == Pos.LEFT else sci_p.rtrig
            mode, ev = self._trig_evts[pos]
            if trigval != trigval_prev:
                if self._trig_axes_callbacks[pos]:
                    self._trig_axes_callbacks[pos](self, pos, trigval)
                elif self._trig_modes[pos] == TrigModes.AXIS:
                    syn.add(mode)
                    self._uip[mode].axisEvent(ev, trigval)
            elif self._trig_modes[pos] == TrigModes.BUTTON:
                if self._trig_s[pos] is None and trigval > min(trigval_prev + 10, 200):
                    self._trig_s[pos] = max(0, min(trigval - 10, 180))
                    _keypressed(mode, ev)
                elif self._trig_s[pos] is not None and trigval <= self._trig_s[pos]:
                    self._trig_s[pos] = None
                    _keyreleased(mode, ev)


        # Manage Stick
        if sci.buttons & SCButtons.LPADTOUCH != SCButtons.LPADTOUCH:
            x, y = sci.lpad_x, sci.lpad_y
            x_p, y_p = sci_p.lpad_x, sci_p.lpad_y

            if self._stick_axes_callback is not None and (x != x_p or y != y_p):
                self._stick_axes_callback(self, x, y)

            if self._stick_mode == StickModes.AXIS:
                revert = self._stick_rev
                (xmode, xev), (ymode, yev) = self._stick_evts # pylint: disable=E0632
                if x != x_p:
                    syn.add(xmode)
                    self._uip[xmode].axisEvent(xev, x)
                if y != y_p:
                    syn.add(ymode)
                    self._uip[ymode].axisEvent(yev, y if not revert else -y)

            elif self._stick_mode == StickModes.BUTTON:

                tmode, tev = self._stick_evts[0]
                lmode, lev = self._stick_evts[1]
                bmode, bev = self._stick_evts[2]
                rmode, rev = self._stick_evts[3]

                # top
                if self._stick_tys is None and y > 0 and y > min(y_p + 2000, 32000):
                    self._stick_tys = max(0, min(y - 2000, 31000))
                    _keypressed(tmode, tev)
                elif self._stick_tys is not None and y <= self._stick_tys:
                    self._stick_tys = None
                    _keyreleased(tmode, tev)

                # left
                if self._stick_lxs is None and x < 0 and x < max(x_p - 2000, -32000):
                    self._stick_lxs = min(0, max(x + 2000, -31000))
                    _keypressed(lmode, lev)
                elif self._stick_lxs is not None and x >= self._stick_lxs:
                    self._stick_lxs = None
                    _keyreleased(lmode, lev)

                # bottom
                if self._stick_bys is None and y < 0 and y < max(y_p - 2000, -32000):
                    self._stick_bys = min(0, max(y + 2000, -31000))
                    _keypressed(bmode, bev)
                elif self._stick_bys is not None and y >= self._stick_bys:
                    self._stick_bys = None
                    _keyreleased(bmode, bev)

                # right
                if self._stick_rxs is None and x > 0 and x > min(x_p + 2000, 32000):
                    self._stick_rxs = max(0, min(x - 2000, 31000))
                    _keypressed(rmode, rev)
                elif self._stick_rxs is not None and x <= self._stick_rxs:
                    self._stick_rxs = None
                    _keyreleased(rmode, rev)
            if sci.buttons & SCButtons.LPAD == SCButtons.LPAD:
                if self._stick_pressed_callback is not None:
                    self._stick_pressed_callback(self)


        if len(_pressed):
            self._uip[Modes.KEYBOARD].pressEvent(_pressed)

        if len(_released):
            self._uip[Modes.KEYBOARD].releaseEvent(_released)

        for i in list(syn):
            self._uip[i].synEvent()


    def setButtonAction(self, btn, key_event):
        for mode in Modes:
            if self._uip[mode].keyManaged(key_event):
                self._btn_map[btn] = (mode, key_event)
                return

    def setButtonCallback(self, btn, callback):
        """
        set callback function to be executed when button is clicked
        callback is called with parameters self(EventMapper), btn
        and pushed (boollean True -> Button pressed, False -> Button released)

        @param btn                      Button
        @param function callback        Callback function
        """

        self._btn_map[btn] = (Modes.CALLBACK, callback)


    def setPadButtons(self, pos, key_events, deadzone=0.6, clicked=False):
        """
        Set pad as buttons

        @param Pos pos          designate left or right pad
        @param list key_events  list of key events for the pad buttons (top,left,bottom,right)
        @param fload deadzone   portion of the pad in the center dead zone from 0.0 to 1.0
        @param bool clicked     action on touch or on click event
        """

        assert len(key_events) == 4
        assert deadzone >= 0.0 and deadzone < 1.0

        self._pad_modes[pos] = PadModes.BUTTONCLICK if clicked else PadModes.BUTTONTOUCH

        self._pad_evts[pos] = []
        for ev in key_events:
            for mode in Modes:
                if self._uip[mode].keyManaged(ev):
                    self._pad_evts[pos].append((mode, ev))
                    break

        self._pad_dzones[pos] = 32768 * deadzone

        if clicked:
            if pos == Pos.LEFT:
                self._btn_map[SCButtons.LPAD] = (None, 0)
            else:
                self._btn_map[SCButtons.RPAD] = (None, 0)

    def setPadButtonCallback(self, pos, callback, clicked=False):
        """
        set callback function to be executed when Pad clicked or touched
        if clicked is False callback will be called with pad, xpos and ypos
        else with pad and boolean is_pressed

        @param Pos pos          designate left or right pad
        @param callback         Callback function
        @param bool clicked     callback on touch or on click event
        """
        if not clicked:
            self._pad_modes[pos] = PadModes.BUTTONTOUCH
            self._pad_evts[pos].append((Modes.CALLBACK, callback))
        else:
            self._pad_modes[pos] = PadModes.BUTTONCLICK
            if pos == Pos.LEFT:
                self._btn_map[SCButtons.LPAD] = (Modes.CALLBACK, callback)
            else:
                self._btn_map[SCButtons.RPAD] = (Modes.CALLBACK, callback)

    def setPadAxesAsButtons(self, pos, abs_events, deadzone=0.6, clicked=False, revert=True):
        """
        Set pad as buttons

        @param Pos pos          designate left or right pad
        @param list key_events  list of axes events for the pad buttons (X, Y)
        @param fload deadzone   portion of the pad in the center dead zone from 0.0 to 1.0
        @param bool clicked     action on touch or on click event
        @param bool revert      revert axes
        """

        assert len(abs_events) == 2
        assert deadzone >= 0.0 and deadzone < 1.0

        self._pad_modes[pos] = PadModes.BUTTONCLICK if clicked else PadModes.BUTTONTOUCH

        self._pad_evts[pos] = []
        for ev in abs_events:
            self._pad_evts[pos].append((Modes.GAMEPAD, ev))

        self._pad_revs[pos] = revert
        self._pad_dzones[pos] = 32768 * deadzone

        if clicked:
            if pos == Pos.LEFT:
                self._btn_map[SCButtons.LPAD] = (None, 0)
            else:
                self._btn_map[SCButtons.RPAD] = (None, 0)


    def setPadMouse(self, pos,
                    trackball=True,
                    friction=sui.Mouse.DEFAULT_FRICTION,
                    xscale=sui.Mouse.DEFAULT_XSCALE,
                    yscale=sui.Mouse.DEFAULT_XSCALE):
        if not trackball:
            friction = 100.0
        self._uip[Modes.MOUSE].updateParams(friction=friction, xscale=xscale, yscale=yscale)
        self._pad_modes[pos] = PadModes.MOUSE


    def setPadScroll(self, pos,
                     trackball=True,
                     friction=sui.Mouse.DEFAULT_SCR_FRICTION,
                     xscale=sui.Mouse.DEFAULT_SCR_XSCALE,
                     yscale=sui.Mouse.DEFAULT_SCR_XSCALE):
        if not trackball:
            friction = 100.0
        self._uip[Modes.MOUSE].updateScrollParams(friction=friction, xscale=xscale, yscale=yscale)
        self._pad_modes[pos] = PadModes.MOUSESCROLL

    def setPadAxes(self, pos, abs_x_event, abs_y_event, revert=True):
        self._pad_modes[pos] = PadModes.AXIS
        self._pad_evts[pos] = [(Modes.GAMEPAD, abs_x_event),
                               (Modes.GAMEPAD, abs_y_event)]
        self._pad_revs[pos] = revert

    def setTrigButton(self, pos, key_event):
        self._trig_modes[pos] = TrigModes.BUTTON
        for mode in Modes:
            if self._uip[mode].keyManaged(key_event):
                self._trig_evts[pos] = (mode, key_event)
                return

    def setTrigAxis(self, pos, abs_event):
        self._trig_modes[pos] = TrigModes.AXIS
        self._trig_evts[pos] = (Modes.GAMEPAD, abs_event)

    def setTrigAxesCallback(self, pos, callback):
            self._trig_modes[pos] = StickModes.AXIS
            self._trig_axes_callbacks[pos] = callback

    def setStickAxes(self, abs_x_event, abs_y_event, revert=True):
        self._stick_mode = StickModes.AXIS
        self._stick_evts = [(Modes.GAMEPAD, abs_x_event),
                            (Modes.GAMEPAD, abs_y_event)]
        self._stick_rev = revert

    def setStickAxesCallback(self, callback):
        """
        Set Callback on StickAxes Movement
        the function will be called with EventMapper, pos_x, pos_y

        @param function callback       the callback function
        """
        self._stick_axes_callback = callback


    def setStickButtons(self, key_events):
        """
        Set stick as buttons

        @param list key_events  list of key events for the pad buttons (top,left,bottom,right)
        """

        assert len(key_events) == 4

        self._stick_mode = StickModes.BUTTON

        self._stick_evts = []
        for ev in key_events:
            for mode in Modes:
                if self._uip[mode].keyManaged(ev):
                    self._stick_evts.append((mode, ev))
                    break

    def setStickPressedCallback(self, callback):
        """
        Set callback on StickPressed event.
        the function will be called with EventMapper as first (and only) argument

        @param function Callback function      function that is called on buton press.
        """
        self._stick_pressed_callback = callback
