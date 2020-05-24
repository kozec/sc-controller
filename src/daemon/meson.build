platform_dependent_src = []
platform_dependent_deps = []
platform_dependent_args = []
platform_dependent_link_with = []
platform_dependent_link_args = []

if host_machine.system() == 'linux'
	platform_dependent_deps += [
		meson.get_compiler('c').find_library('dl'),
		dependency('x11'),
	]
	platform_dependent_src += [
		'device_monitor_linux.c',
		'input_libusb.c',
	]
	if get_option('use-hidapi').enabled()
		platform_dependent_deps += [ dependency('hidapi-hidraw') ]
		platform_dependent_args += [ '-DUSE_HIDAPI' ]
		platform_dependent_src += [ 'input_hidapi.c' ]
	endif
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
		'input_bsd.c',
	]
elif host_machine.system() == 'windows'
	if not (get_option('use-hidapi').auto() or get_option('use-hidapi').enabled())
		error('use-hidapi option cannot be disabled on Windows')
	endif
	if get_option('use-dinput').auto() or get_option('use-dinput').enabled()
		platform_dependent_deps += [
			meson.get_compiler('c').find_library('dinput8'),
			meson.get_compiler('c').find_library('dxguid'),
		]
		platform_dependent_args += [ '-DUSE_DINPUT' ]
		platform_dependent_src += [ 'input_dinput.c' ]
		platform_dependent_link_args += [ '-ldinput8', '-ldxguid' ]
	endif
	platform_dependent_deps = [
		meson.get_compiler('c').find_library('regex'),
		meson.get_compiler('c').find_library('wsock32'),
		meson.get_compiler('c').find_library('setupapi'),
	]
	platform_dependent_link_with += [
		client_lib, msys_socket_lib,
	]
	platform_dependent_src += [
		'device_monitor_win32.c',
		'input_hidapi.c',
		# On Windows, modified hidapi is compiled directly into binary
		'hid.c'
	]
	platform_dependent_link_args += [ '-mconsole' ]
	platform_dependent_args += [ '-DUSE_HIDAPI' ]
else
	error('Unsupported system ' + host_machine.system() + ', please add it here')
endif

scc_daemon = executable('scc-daemon',
	include_directories: include,
	c_args: platform_dependent_args,
	link_with: [ utils_lib, tools_lib, parser_lib, actions_lib,
				 config_lib, virtual_device_lib ] + platform_dependent_link_with,
	link_args: platform_dependent_link_args,
	dependencies: platform_dependent_deps + [
		dependency('zlib'),
	],
	build_rpath: '/usr/X11R6/lib',
	sources: platform_dependent_src + [
		'main.c',
		
		'x11.c',
		'daemon.c',
		'logger.c',
		'socket.c',
		'poller.c',
		'mapper.c',
		'command.c',
		'drivers.c',
		'locking.c',
		'scheduler.c',
		'device_monitor.c',
		'cemuhook_server.c',
	],
)

scc_input_tester = executable('scc-input-tester',
	include_directories: include,
	c_args: platform_dependent_args,
	link_with: [ utils_lib, tools_lib ],
	link_args: platform_dependent_link_args,
	dependencies: platform_dependent_deps + [
		dependency('zlib'),
	],
	sources: platform_dependent_src + [
		'input_tester.c',
		
		'poller.c',
		'drivers.c',
		'scheduler.c',
		'device_monitor.c',
	],
)

run_target('scc-daemon', command: ['sh', '../../meson-run.sh', 'src/daemon/scc-daemon', 'debug'],
	dependencies: [scc_daemon])

run_target('scc-input-tester', command: ['sh', '../../meson-run.sh', 'src/daemon/scc-input-tester', '--first'],
	dependencies: [scc_input_tester])

