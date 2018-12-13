platform_dependent_deps = []

if host_machine.system() == 'linux'
	# subdir('uinput')
	subdir('uinput-x11')
elif host_machine.system() == 'openbsd'
	subdir('uinput-x11')
elif host_machine.system() == 'windows'
	subdir('uinput-win32')
elif host_machine.system() == 'openbsd'
	error('BSD')
else
	error('Unsupported system ' + host_machine.system() + ', please add it here')
endif

if host_machine.system() == 'windows'
	platform_dependent_deps = [
		meson.get_compiler('c').find_library('regex'),
		meson.get_compiler('c').find_library('wsock32'),
		meson.get_compiler('c').find_library('libusb-1.0'),
	]
else
	platform_dependent_deps = [
		meson.get_compiler('c').find_library('dl'),
		meson.get_compiler('c').find_library('X11'),
	]
	if get_option('android').disabled()
		platform_dependent_deps += [
			dependency('libudev'),
			meson.get_compiler('c').find_library('libusb-1.0'),
		]
	endif
endif


executable('scc-daemon',
	include_directories: include,
	link_with: [utils_lib, tools_lib, parser_lib,
				actions_lib, config_lib, uinput_lib],
	dependencies: platform_dependent_deps,
	sources: [
		'x11.c',
		'daemon.c',
		'socket.c',
		'poller.c',
		'mapper.c',
		'command.c',
		'drivers.c',
		'locking.c',
		'scheduler.c',
		'usb_helper.c',
		'device_monitor.c',
	],
)
