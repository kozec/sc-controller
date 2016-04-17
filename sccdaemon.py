#!/usr/bin/python2
from scc.sccdaemon import SCCDaemon
from scc.tools import init_logging

import os, argparse

if __name__ == '__main__':

	def _main():
		init_logging()
		parser = argparse.ArgumentParser(description=__doc__)
		parser.add_argument('profile', type=str)
		parser.add_argument('command', type=str, choices=['start', 'stop', 'restart', 'debug'])
		pid_file = os.path.expanduser('~/.scccontroller.pid')
		socket_file = os.path.expanduser('~/.scccontroller.socket')
		daemon = SCCDaemon(pid_file, socket_file)
		args = parser.parse_args()
		daemon.load_profile(args.profile)

		if 'start' == args.command:
			daemon.start()
		elif 'stop' == args.command:
			daemon.stop()
		elif 'restart' == args.command:
			daemon.restart()
		elif 'debug' == args.command:
			daemon.debug()

	_main()
