#!/usr/bin/python2
import argparse

from scc.controller import SCController
from scc.constants import SCButtons
from scc.mapper import Mapper
from scc.uinput import Keys, Axes
from scc.daemon import Daemon


class SCDaemon(Daemon):
	def __init__(self, mapper, piddile):
		Daemon.__init__(self, piddile)
		self.mapper = mapper

	def run(self):
		sc = SCController(callback=self.mapper.callback)
		sc.run()


if __name__ == '__main__':

	def _main():
		parser = argparse.ArgumentParser(description=__doc__)
		parser.add_argument('profile', type=str)
		parser.add_argument('command', type=str, choices=['start', 'stop', 'restart', 'debug'])
		args = parser.parse_args()
		mapper = Mapper(args.profile)
		daemon = SCDaemon(mapper, '/tmp/scccontroller.pid')

		if 'start' == args.command:
			daemon.start()
		elif 'stop' == args.command:
			daemon.stop()
		elif 'restart' == args.command:
			daemon.restart()
		elif 'debug' == args.command:
			try:
				sc = SCController(callback=mapper.callback)
				sc.run()
			except KeyboardInterrupt:
				return

	_main()
