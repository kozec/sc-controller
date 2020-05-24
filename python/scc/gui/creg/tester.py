#!/usr/bin/env python2
"""
SC-Controller - Controller Registration - Tester

Wrapper around `scc-input-tester` utility
"""
from gi.repository import GObject, Gio, GLib
from scc.tools import find_binary

import sys, logging, platform
log = logging.getLogger("CReg.Tester")

if platform.system() == "Windows":
	from ctypes import POINTER, byref, CDLL, c_bool, c_int
	from ctypes.wintypes import HWND, LPVOID, DWORD
	import os, sys
	LPDWORD = POINTER(DWORD)
	lib_kernel32 = CDLL("kernel32")
	lib_kernel32.PeekNamedPipe.restype = c_bool
	lib_kernel32.PeekNamedPipe.argtypes = [ HWND, LPVOID, DWORD, LPDWORD, LPDWORD, LPDWORD ]
	lib_c = CDLL("msvcrt")
	lib_c._get_osfhandle.restype = HWND
	lib_c._get_osfhandle.argtypes = [ c_int ]


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
	
	def __init__(self, driver, device_id, name, device_path):
		GObject.GObject.__init__(self)
		self.buffer = b""
		self.buttons = []
		self.axes = []
		self.driver = driver
		self.device_name = name
		self.device_path = device_path
		self.device_id = device_id
		self.subprocess = None
		self.errorred = False	# To prevent sending 'error' signal multiple times
	
	
	def __del__(self):
		if self.subprocess:
			if platform.system() == "Windows":
				self.subprocess.kill()
			else:
				self.subprocess.send_signal(9)
	
	
	def start(self):
		""" Starts driver test subprocess """
		cmd = [ find_binary("scc-input-tester"), self.device_path ]
		
		try:
			if platform.system() == "Windows":
				from subprocess import Popen, PIPE, STARTUPINFO, STARTF_USESHOWWINDOW
				sinfo = STARTUPINFO()
				sinfo.dwFlags = STARTF_USESHOWWINDOW
				sinfo.wShowWindow = 0
				self.subprocess = Popen(cmd, stdout=PIPE, startupinfo=sinfo)
				self.subprocess._osfhandle = lib_c._get_osfhandle(self.subprocess.stdout.fileno())
				GLib.idle_add(self._check)
			else:
				flags = Gio.SubprocessFlags.STDOUT_PIPE
				self.subprocess = Gio.Subprocess.new(cmd, flags)
				self.subprocess.wait_async(None, self._on_finished)
				(self.subprocess.get_stdout_pipe()
						.read_bytes_async(32, 0, None, self._on_read))
		except Exception as a:
			print str(e)
			sys.stdout.flush()
	
	
	def stop(self):
		if self.subprocess:
			if platform.system() == "Windows":
				self.subprocess.kill()
			else:
				self.subprocess.send_signal(2)	# Sigint
	
	
	def _check(self, *a):
		"""
		Repeatedly check status and data from subprocess.
		Used only on windows
		"""
		try:
			if self.subprocess is None:
				return False
			self.subprocess.poll()
			if self.subprocess.returncode is not None:
				if self.subprocess.returncode == 0:
					self.emit('finished')
				else:
					self.errorred = True
					self.emit('error', self.subprocess.returncode)
				return False
			(read, n_avail, n_message) = DWORD(), DWORD(), DWORD()
			lib_kernel32.PeekNamedPipe(self.subprocess._osfhandle, None, 0,
					byref(read), byref(n_avail), byref(n_message))
			if n_avail:
				self._on_line(self.subprocess.stdout.readline().strip("\r\n"))
			sys.stdout.flush()
			return True
		except Exception as e:
			print str(e)
			sys.stdout.flush()
			return True
	
	
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
		""" Not called under Windows """
		sys.stdout.flush()
		try:
			data = stream.read_bytes_finish(result).get_data()
		except Exception, e:
			log.exception(e)
			self.subprocess.send_signal(2)	# Siging
			if not self.errorred:
				self.errorred = True
				self.emit('error', 1)
			return
		sys.stdout.flush()
		if len(data) > 0:
			stream.read_bytes_async(32, 0, None, self._on_read)
		return
		
		if len(data) > 0:
			self.buffer += data
			while "\n" in self.buffer:
				line, self.buffer = self.buffer.split("\n", 1)
				sys.stdout.flush()
				try:
					self._on_line(line)
				except Exception, e:
					log.exception(e)
			stream.read_bytes_async(32, 0, None, self._on_read)
	
	
	def _on_line(self, line):
		sys.stdout.flush()
		if line.startswith("axis_update"):
			trash, number, value = line.split("\t")
			number, value = int(number), int(value)
			self.emit('axis', number, value)
		elif line.startswith("button_press"):
			trash, code = line.split("\t")
			self.emit('button', int(code), True)
		elif line.startswith("button_release"):
			trash, code = line.split("\t")
			self.emit('button', int(code), False)
		elif line.startswith("Ready."):
			# print "REAAAAAAAAAAAAAADY"
			self.emit('ready')
		elif line.startswith("axes:"):
			self.axes = [ int(x) for x in line.split(" ")[1:] if len(x.strip()) ]
		elif line.startswith("buttons:"):
			self.buttons = [ int(x) for x in line.split(" ")[1:] if len(x.strip()) ]

