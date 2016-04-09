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

import usb1
from collections import namedtuple
import struct
from enum import IntEnum

from threading import Timer
import time

VENDOR_ID = 0x28de
PRODUCT_ID = [0x1102, 0x1142]
ENDPOINT = [3, 2]
CONTROLIDX = [2, 1]

HPERIOD  = 0.02
LPERIOD  = 0.5
DURATION = 1.0

STEAM_CONTROLER_FORMAT = [
    ('x',   'ukn_00'),
    ('x',   'ukn_01'),
    ('H',   'status'),
    ('H',   'seq'),
    ('x',   'ukn_02'),
    ('I',   'buttons'),
    ('B',   'ltrig'),
    ('B',   'rtrig'),
    ('x',   'ukn_03'),
    ('x',   'ukn_04'),
    ('x',   'ukn_05'),
    ('h',   'lpad_x'),
    ('h',   'lpad_y'),
    ('h',   'rpad_x'),
    ('h',   'rpad_y'),
    ('10x', 'ukn_06'),
    ('h',   'gpitch'),
    ('h',   'groll'),
    ('h',   'gyaw'),
    ('h',   'q1'),
    ('h',   'q2'),
    ('h',   'q3'),
    ('h',   'q4'),
    ('16x', 'ukn_07'),
]

_FORMATS, _NAMES = zip(*STEAM_CONTROLER_FORMAT)

SteamControllerInput = namedtuple('SteamControllerInput', ' '.join([x for x in _NAMES if not x.startswith('ukn_')]))

SCI_NULL = SteamControllerInput._make(struct.unpack('<' + ''.join(_FORMATS), b'\x00' * 64))

class SCStatus(IntEnum):
    IDLE  = 2820
    INPUT = 15361
    EXIT  = 259

class SCButtons(IntEnum):
    RPADTOUCH = 0b00010000000000000000000000000000
    LPADTOUCH = 0b00001000000000000000000000000000
    RPAD      = 0b00000100000000000000000000000000
    LPAD      = 0b00000010000000000000000000000000 # Same for stick but without LPadTouch
    RGRIP     = 0b00000001000000000000000000000000
    LGRIP     = 0b00000000100000000000000000000000
    START     = 0b00000000010000000000000000000000
    STEAM     = 0b00000000001000000000000000000000
    BACK      = 0b00000000000100000000000000000000
    A         = 0b00000000000000001000000000000000
    X         = 0b00000000000000000100000000000000
    B         = 0b00000000000000000010000000000000
    Y         = 0b00000000000000000001000000000000
    LB        = 0b00000000000000000000100000000000
    RB        = 0b00000000000000000000010000000000
    LT        = 0b00000000000000000000001000000000
    RT        = 0b00000000000000000000000100000000

class HapticPos(IntEnum):
    """Specify witch pad or trig is used"""
    RIGHT = 0
    LEFT = 1

class SteamController(object):

    def __init__(self, callback, callback_args=None):
        """
        Constructor

        callback: function called on usb message must take at lead a
        SteamControllerInput as first argument

        callback_args: Optional arguments passed to the callback afer the
        SteamControllerInput argument
        """
        self._handle = None
        self._cb = callback
        self._cb_args = callback_args
        self._cmsg = []
        self._ctx = usb1.USBContext()


        for i in range(len(PRODUCT_ID)):
            pid = PRODUCT_ID[i]
            endpoint = ENDPOINT[i]
            ccidx = CONTROLIDX[i]

            self._handle = self._ctx.openByVendorIDAndProductID(
                VENDOR_ID, pid,
                skip_on_error=True,
            )
            if self._handle is not None:
                break

        if self._handle is None:
            raise ValueError('SteamControler Device not found')

        self._ccidx = ccidx
        dev = self._handle.getDevice()
        cfg = dev[0]

        for inter in cfg:
            for setting in inter:
                number = setting.getNumber()
                if self._handle.kernelDriverActive(number):
                    self._handle.detachKernelDriver(number)
                if (setting.getClass() == 3 and
                    setting.getSubClass() == 0 and
                    setting.getProtocol() == 0):
                    self._handle.claimInterface(number)

        self._transfer_list = []
        transfer = self._handle.getTransfer()
        transfer.setInterrupt(
            usb1.ENDPOINT_IN | endpoint,
            64,
            callback=self._processReceivedData,
        )
        transfer.submit()
        self._transfer_list.append(transfer)

        self._period = LPERIOD

        if pid == 0x1102:
            self._timer = Timer(LPERIOD, self._callbackTimer)
            self._timer.start()
        else:
            self._timer = None

        self._tup = None
        self._lastusb = time.time()

        # Disable Haptic auto feedback

        self._ctx.handleEvents()
        self._sendControl(struct.pack('>' + 'I' * 1,
                                      0x81000000))
        self._ctx.handleEvents()
        self._sendControl(struct.pack('>' + 'I' * 6,
                                      0x87153284,
                                      0x03180000,
                                      0x31020008,
                                      0x07000707,
                                      0x00300000,
                                      0x2f010000))
        self._ctx.handleEvents()


    def __del__(self):
        if self._handle:
            self._handle.close()

    def _sendControl(self, data, timeout=0):

        zeros = b'\x00' * (64 - len(data))

        self._handle.controlWrite(request_type=0x21,
                                  request=0x09,
                                  value=0x0300,
                                  index=self._ccidx,
                                  data=data + zeros,
                                  timeout=timeout)

    def addFeedback(self, position, amplitude=128, period=0, count=1):
        """
        Add haptic feedback to be send on next usb tick

        @param int position     haptic to use 1 for left 0 for right
        @param int amplitude    signal amplitude from 0 to 65535
        @param int period       signal period from 0 to 65535
        @param int count        number of period to play
        """
        self._cmsg.insert(0, struct.pack('<BBBHHH', 0x8f, 0x07, position, amplitude, period, count))

    def _processReceivedData(self, transfer):
        """Private USB async Rx function"""

        if (transfer.getStatus() != usb1.TRANSFER_COMPLETED or
            transfer.getActualLength() != 64):
            return

        data = transfer.getBuffer()
        self._tup = SteamControllerInput._make(struct.unpack('<' + ''.join(_FORMATS), data))
        self._callback()

        transfer.submit()

    def _callback(self):

        if self._tup is None or self._tup.status != SCStatus.INPUT:
            return

        self._lastusb = time.time()

        if isinstance(self._cb_args, (list, tuple)):
            self._cb(self, self._tup, *self._cb_args)
        else:
            self._cb(self, self._tup)



        self._period = HPERIOD

    def _callbackTimer(self):

        d = time.time() - self._lastusb
        self._timer.cancel()

        if d > DURATION:
            self._period = LPERIOD

        self._timer = Timer(self._period, self._callbackTimer)
        self._timer.start()

        if self._tup is None:
            return

        if d < HPERIOD:
            return

        if isinstance(self._cb_args, (list, tuple)):
            self._cb(self, self._tup, *self._cb_args)
        else:
            self._cb(self, self._tup)


    def run(self):
        """Fucntion to run in order to process usb events"""
        if self._handle:
            try:
                while any(x.isSubmitted() for x in self._transfer_list):
                    self._ctx.handleEvents()
                    if len(self._cmsg) > 0:
                        cmsg = self._cmsg.pop()
                        self._sendControl(cmsg)

            except usb1.USBErrorInterrupted:
                pass


    def handleEvents(self):
        """Fucntion to run in order to process usb events"""
        if self._handle and self._ctx:
            self._ctx.handleEvents()
