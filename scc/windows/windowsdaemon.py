#!/usr/bin/python2
from __future__ import unicode_literals
import sys, os, atexit

class WindowsDaemon(object):
	
	def __init__(self, pidfile):
		self.pidfile = pidfile

	def daemonize(self):
		# On windows? Don't be silly
		pass
	
	def write_pid(self):
		"""Write pid file"""
		atexit.register(self.delpid)

		pid = str(os.getpid())
		with open(self.pidfile, 'w+') as fd:
			fd.write(pid + '\n')

	def delpid(self):
		"""Delete pid file"""
		os.remove(self.pidfile)

	def start(self):
		"""Start the daemon."""

		# Check for a pidfile to see if the daemon already runs
		try:
			with open(self.pidfile, 'r') as pidf:
				pid = int(pidf.read().strip())
		except Exception:
			pid = None

		if pid:
			message = "pidfile {0} already exist. " + \
					"Daemon already running?\n"
			sys.stderr.write(message.format(self.pidfile))
			sys.exit(1)
		
		# Start the daemon
		self.on_start()
		while True:
			try:
				self.run()
			except:
				pass
	
	def on_start(self):
		pass
	
	def stop(self):
		# There is no daemonization, so there is no stopping
		# Implement sigkill or pray to god
		pass

	def restart(self):
		"""Restart the daemon."""
		sys.stderr.write("Restart not supported")
		sys.exit(1)

	def run(self):
		"""You should override this method when you subclass Daemon.

		It will be called after the process has been daemonized by
		start() or restart()."""
		pass
