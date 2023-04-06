#!/usr/bin/env python3
"""
SC-Controller - Controller Registration - Tester

Class that interacts with `scc hid_test` and `scc evdev_test` commands.
"""
from gi.repository import GObject, Gio
from scc.tools import find_binary

import logging
log = logging.getLogger("CReg.Tester")


class Tester(GObject.GObject):
	"""
	List of signals:
		ready ()
			Emited when subprocess signalizes it's ready to send data
		error (code)
			Emited when driver test subprocess exits with non-zero return code
		finished ()
			Emited when driver test subprocess exits with zero return code
		axis (number, value)
			Emited when position on axis is changed
		button (keycode, pressed)
			Emited when button on tested gamepad is pressed or released
	"""

	__gsignals__ = {
		b"error"		: (GObject.SignalFlags.RUN_FIRST, None, (int, )),
		b"ready"		: (GObject.SignalFlags.RUN_FIRST, None, ()),
		b"finished"		: (GObject.SignalFlags.RUN_FIRST, None, ()),
		b"axis"			: (GObject.SignalFlags.RUN_FIRST, None, (int, int)),
		b"button"		: (GObject.SignalFlags.RUN_FIRST, None, (int, bool)),
	}
	
	def __init__(self, driver, device_id):
		GObject.GObject.__init__(self)
		self.buffer = b""
		self.buttons = []
		self.axes = []
		self.subprocess = None
		self.driver = driver
		self.device_id = device_id
		self.errorred = False	# To prevent sending 'error' signal multiple times
	
	
	def __del__(self):
		if self.subprocess:
			self.subprocess.send_signal(9)
	
	
	def start(self):
		""" Starts driver test subprocess """
		cmd = [find_binary("scc")] + ["test_" + self.driver, self.device_id]
		self.subprocess = Gio.Subprocess.new(cmd, Gio.SubprocessFlags.STDOUT_PIPE)
		self.subprocess.wait_async(None, self._on_finished)
		self.subprocess.get_stdout_pipe().read_bytes_async(
			32, 0, None, self._on_read)
	
	
	def stop(self):
		if self.subprocess:
			self.subprocess.send_signal(2)	# Sigint
	
	
	def _on_finished(self, subprocess, result):
		subprocess.wait_finish(result)
		if self.errorred:
			return
		if subprocess.get_exit_status() == 0:
			self.emit('finished')
		else:
			self.errorred = True
			self.emit('error', subprocess.get_exit_status())
	
	
	def _on_read(self, stream, result):
		try:
			data = stream.read_bytes_finish(result).get_data()
		except Exception as e:
			log.exception(e)
			self.subprocess.send_signal(2)
			if not self.errorred:
				self.errorred = True
				self.emit('error', 1)
			return
		if len(data) > 0:
			self.buffer += data
			while "\n" in self.buffer:
				line, self.buffer = self.buffer.split("\n", 1)
				try:
					self._on_line(line)
				except Exception as e:
					log.exception(e)
			self.subprocess.get_stdout_pipe().read_bytes_async(
				32, 0, None, self._on_read)
	
	
	def _on_line(self, line):
		if line.startswith("Axis"):
			trash, number, value = line.split(" ")
			number, value = int(number), int(value)
			self.emit('axis', number, value)
		elif line.startswith("ButtonPress"):
			trash, code = line.split(" ")
			self.emit('button', int(code), True)
		elif line.startswith("ButtonRelease"):
			trash, code = line.split(" ")
			self.emit('button', int(code), False)
		elif line.startswith("Ready"):
			self.emit('ready')
		elif line.startswith("Axes:"):
			self.axes = [ int(x) for x in line.split(" ")[1:] if len(x.strip()) ]
		elif line.startswith("Buttons:"):
			self.buttons = [ int(x) for x in line.split(" ")[1:] if len(x.strip()) ]
