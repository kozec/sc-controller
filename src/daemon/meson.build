platform_dependent_deps = []

if host_machine.system() == 'linux'
	subdir('uinput')
	platform_dependent_deps = [
		meson.get_compiler('c').find_library('dl'),
		dependency('x11'),
	]
	if get_option('android').disabled()
		platform_dependent_deps += [
			dependency('libudev'),
			meson.get_compiler('c').find_library('libusb-1.0'),
		]
	endif
elif host_machine.system() == 'openbsd'
	subdir('uinput-x11')
	include += [ include_directories('/usr/local/include') ]
	platform_dependent_deps = [
		dependency('x11'),
		dependency('libusb-1.0'),
	]
elif host_machine.system() == 'windows'
	subdir('uinput-win32')
	platform_dependent_deps = [
		meson.get_compiler('c').find_library('regex'),
		meson.get_compiler('c').find_library('wsock32'),
		meson.get_compiler('c').find_library('libusb-1.0'),
	]
elif host_machine.system() == 'openbsd'
	subdir('uinput-x11')
else
	error('Unsupported system ' + host_machine.system() + ', please add it here')
endif


executable('scc-daemon',
	include_directories: include,
	link_with: [utils_lib, tools_lib, parser_lib,
				actions_lib, config_lib, uinput_lib],
	dependencies: platform_dependent_deps,
	build_rpath: '/usr/X11R6/lib',
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
