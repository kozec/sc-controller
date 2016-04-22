#!/usr/bin/env python2

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

from threading import Timer
import struct, time

from scc.lib import usb1
from scc.constants import VENDOR_ID, PRODUCT_ID, HPERIOD, LPERIOD, DURATION
from scc.constants import ENDPOINT, CONTROLIDX, FORMATS, ControllerInput
from scc.constants import SCStatus, SCButtons, HapticPos

class SCController(object):

	def __init__(self, callback, callback_args=None):
		"""
		Constructor

		callback: function called on usb message must take at lead a
		ControllerInput as first argument

		callback_args: Optional arguments passed to the callback afer the
		ControllerInput argument
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
			raise ValueError('Controler Device not found')

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

		@param int position	 haptic to use 1 for left 0 for right
		@param int amplitude	signal amplitude from 0 to 65535
		@param int period	   signal period from 0 to 65535
		@param int count		number of period to play
		"""
		self._cmsg.insert(0, struct.pack('<BBBHHH', 0x8f, 0x07, position, amplitude, period, count))

	def _processReceivedData(self, transfer):
		"""Private USB async Rx function"""

		if (transfer.getStatus() != usb1.TRANSFER_COMPLETED or
			transfer.getActualLength() != 64):
			return

		data = transfer.getBuffer()
		self._tup = ControllerInput._make(struct.unpack('<' + ''.join(FORMATS), data))
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
