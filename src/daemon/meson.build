platform_dependent_deps = []
platform_dependent_src = []

if host_machine.system() == 'linux'
	platform_dependent_deps = [
		meson.get_compiler('c').find_library('dl'),
		dependency('x11'),
	]
	platform_dependent_src = [
		'device_monitor_linux.c',
		'usb_helper.c',
	]
	if get_option('android').disabled()
		platform_dependent_deps += [
			dependency('libudev'),
			meson.get_compiler('c').find_library('libusb-1.0'),
		]
	endif
elif host_machine.system() == 'openbsd' or host_machine.system() == 'netbsd'
	USB_HELPER = 'usb_helper_bsd.c'
	if host_machine.system() == 'openbsd'
		# not needed on netbsd
		include += [ include_directories('/usr/local/include') ]
	endif
	platform_dependent_deps = [
		dependency('x11'),
		meson.get_compiler('c').find_library('libusbhid'),
	]
	platform_dependent_src = [
		'device_monitor_bsd.c',
		'usb_helper_bsd.c',
	]
elif host_machine.system() == 'windows'
	platform_dependent_deps = [
		meson.get_compiler('c').find_library('regex'),
		meson.get_compiler('c').find_library('wsock32'),
		meson.get_compiler('c').find_library('libusb-1.0'),
	]
	platform_dependent_src = [
		'device_monitor_win32.c',
		'usb_helper.c',
	]
else
	error('Unsupported system ' + host_machine.system() + ', please add it here')
endif


executable('scc-daemon',
	include_directories: include,
	link_with: [ utils_lib, tools_lib, parser_lib,
				 actions_lib, config_lib, virtual_device_lib ],
	dependencies: platform_dependent_deps,
	build_rpath: '/usr/X11R6/lib',
	sources: platform_dependent_src + [
		'x11.c',
		'main.c',
		'daemon.c',
		'socket.c',
		'poller.c',
		'mapper.c',
		'command.c',
		'drivers.c',
		'locking.c',
		'scheduler.c',
	],
)
