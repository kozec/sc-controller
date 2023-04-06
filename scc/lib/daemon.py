#!/usr/bin/env python2

"""Generic linux daemon base class"""

# Adapted from http://www.jejik.com/files/examples/daemon3x.py
# thanks to the original author

import sys
import os
import time
import atexit
import signal
import syslog

class Daemon(object):
	"""A generic daemon class.

	Usage: subclass the daemon class and override the run() method."""

	def __init__(self, pidfile):
		self.pidfile = pidfile

	def daemonize(self):
		"""Deamonize class. UNIX double fork mechanism."""

		try:
			pid = os.fork()
			if pid > 0:
				# exit first parent
				sys.exit(0)
		except OSError as err:
			sys.stderr.write('fork #1 failed: {0}\n'.format(err))
			sys.exit(1)

		# decouple from parent environment
		os.chdir('/')
		os.setsid()
		os.umask(0)

		# do second fork
		try:
			pid = os.fork()
			if pid > 0:

				# exit from second parent
				sys.exit(0)
		except OSError as err:
			sys.stderr.write('fork #2 failed: {0}\n'.format(err))
			sys.exit(1)

		# redirect standard file descriptors
		sys.stdout.flush()
		sys.stderr.flush()
		stdi = open(os.devnull, 'r')
		stdo = open(os.devnull, 'a+')
		stde = open(os.devnull, 'a+')

		os.dup2(stdi.fileno(), sys.stdin.fileno())
		os.dup2(stdo.fileno(), sys.stdout.fileno())
		os.dup2(stde.fileno(), sys.stderr.fileno())

		# write pidfile
		self.write_pid()

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
			# Check if PID coresponds to running daemon process and fail if yes
			try:
				assert os.path.exists("/proc")	# Just in case of BSD...
				cmdline = file("/proc/%s/cmdline" % (pid,), "r").read().replace("\x00", " ").strip()
				if sys.argv[0] in cmdline:
					raise Exception("already running")
			except IOError:
				# No such process
				pass
			except:
				message = "pidfile {0} already exist. " + \
						"Daemon already running?\n"
				sys.stderr.write(message.format(self.pidfile))
				sys.exit(1)

			sys.stderr.write("Overwriting stale pidfile\n")

		# Start the daemon
		self.daemonize()
		syslog.syslog(syslog.LOG_INFO, '{}: started'.format(os.path.basename(sys.argv[0])))
		self.on_start()
		while True:
			try:
				self.run()
			except Exception as e: # pylint: disable=W0703
				syslog.syslog(syslog.LOG_ERR, '{}: {!s}'.format(os.path.basename(sys.argv[0]), e))
			time.sleep(2)

	def on_start(self):
		pass
	
	def stop(self, once=False):
		"""Stop the daemon."""

		# Get the pid from the pidfile
		try:
			with open(self.pidfile, 'r') as pidf:
				pid = int(pidf.read().strip())
		except Exception:
			pid = None

		if not pid:
			message = "pidfile {0} does not exist. " + \
					"Daemon not running?\n"
			sys.stderr.write(message.format(self.pidfile))
			return # not an error in a restart

		# Try killing the daemon process
		try:
			for x in range(0, 10): # Waits max 1s
				os.kill(pid, signal.SIGTERM)
				if once: break
				for x in range(50):
					os.kill(pid, 0)
					time.sleep(0.1)
				time.sleep(0.1)
			os.kill(pid, signal.SIGKILL)
		except OSError as err:
			e = str(err.args)
			if e.find("No such process") > 0:
				if os.path.exists(self.pidfile):
					os.remove(self.pidfile)
			else:
				print((str(err.args)))
				sys.exit(1)
		syslog.syslog(syslog.LOG_INFO, '{}: stopped'.format(os.path.basename(sys.argv[0])))

	def restart(self):
		"""Restart the daemon."""
		self.stop()
		time.sleep(2)
		self.start()

	def run(self):
		"""You should override this method when you subclass Daemon.

		It will be called after the process has been daemonized by
		start() or restart()."""
