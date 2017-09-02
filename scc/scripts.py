#!/usr/bin/env python2
"""
SC-Controller - Scripts

Contains code for most of what can be done using 'scc' script.
Created so scc-* stuff doesn't polute /usr/bin.
"""
from scc.tools import init_logging, set_logging_level
import sys, os, subprocess


class InvalidArguments(Exception): pass


def cmd_daemon(argv0, argv):
	""" Controls scc-daemon """
	# Actually just passes parameters to scc-daemon
	scc_daemon = find_binary("scc-daemon")
	subprocess.Popen([scc_daemon] + argv0).communicate()


def help_daemon():
	scc_daemon = find_binary("scc-daemon")
	subprocess.Popen([scc_daemon, "--help"]).communicate()


def cmd_evdev_test(argv0, argv):
	"""
	Evdev driver test. Displays gamepad inputs using evdev driver.
	
	Usage: scc evdev_test /dev/input/node
	Return codes:
	  0 - normal exit
	  1 - invalid arguments or other error
	  2 - failed to open device
	"""
	from scc.drivers.evdevdrv import evdevdrv_test
	return evdevdrv_test(argv)


def cmd_hid_test(argv0, argv):
	"""
	HID driver test. Displays gamepad inputs using hid driver.
	
	Usage: scc hid_test vendor_id device_id
	Return codes:
	  0 - normal exit
	  1 - invalid arguments or other error
	  2 - failed to open device
	  3 - device is not HID-compatibile
	  4 - failed to parse HID descriptor
	"""
	from scc.drivers.hiddrv import hiddrv_test, HIDController
	return hiddrv_test(HIDController, argv)


def show_help(command = None, out=sys.stdout):
	names = [ x[4:] for x in globals() if x.startswith("cmd_") ]
	max_len = max([ len(x) for x in names ])
	if command in names:
		if "help_" + command in globals():
			return globals()["help_" + command]()
		hlp = (globals()["cmd_" + command].__doc__ or "").strip("\t \r\n")
		if hlp:
			lines = hlp.split("\n")
			if len(lines) > 0:
				for line in lines:
					line = (line
						.replace("Usage: scc", "Usage: %s" % (sys.argv[0], )))
					if line.startswith("\t"): line = line[1:]
					print >>out, line
				return 0
	
	print >>out, "Usage: %s <command> [ arguments ]" % (sys.argv[0], )
	print >>out, ""
	print >>out, "List of commands:"
	for name in names:
		hlp = ((globals()["cmd_" + name].__doc__ or "")
					.strip("\t \r\n")
					.split("\n")[0])
		print >>out, (" - %%-%ss %%s" % (max_len, )) % (name, hlp)
	return 0


def main():
	init_logging()
	if len(sys.argv) < 2:
		sys.exit(show_help())
	if "-h" in sys.argv or "--help" in sys.argv:
		while "-h" in sys.argv:
			sys.argv.remove("-h")
		while "--help" in sys.argv:
			sys.argv.remove("--help")
		sys.exit(show_help(sys.argv[1] if len(sys.argv) > 1 else None))
	if "-v" in sys.argv:
		while "-v" in sys.argv:
			sys.argv.remove("-v")
		set_logging_level(True, True)
	else:
		set_logging_level(False, False)
	try:
		command = globals()["cmd_" + sys.argv[1]]
	except:
		print >>sys.stderr, "Unknown command: %s" % (sys.argv[1], )
		sys.exit(show_help(out=sys.stderr))
	
	try:
		sys.exit(command(sys.argv[0], sys.argv[2:]))
	except KeyboardInterrupt:
		sys.exit(0)
	except InvalidArguments:
		print >>sys.stderr, "Invalid arguments"
		print >>sys.stderr, ""
		show_help(sys.argv[1], out=sys.stderr)
		sys.exit(1)
