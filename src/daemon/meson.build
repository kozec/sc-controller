platform_dependent_deps = []
platform_dependent_link = []

if host_machine.system() == 'linux'
	uinput_lib = static_library('uinput',
		include_directories: include,
		sources: [
			'uinput/common.c',
			'uinput/mouse.c',
			'uinput/gamepad.c',
			'uinput/keyboard.c',
			'uinput/keyboard_buttons.c',
		]
	)
	
	platform_dependent_link = [ uinput_lib ]
	platform_dependent_deps = [
		meson.get_compiler('c').find_library('dl'),
	]
	if get_option('android').disabled()
		platform_dependent_deps += [
			dependency('libudev'),
			meson.get_compiler('c').find_library('libusb-1.0'),
		]
	endif
	
elif host_machine.system() == 'windows'
	add_languages('cpp')
	
	libvigemclient = shared_library('vigemclient',
		include_directories: include_directories('win32/vigemclient/include'),
		dependencies: [
			meson.get_compiler('cpp').find_library('setupapi'),
			meson.get_compiler('cpp').find_library('hid'),
		],
		sources: [ 'win32/vigemclient/ViGEmClient.cpp' ],
	)
	
	win32_lib = static_library('win32',
		include_directories: [include, include_directories('win32/vigemclient/include')],
		link_with: libvigemclient,
		sources: [
			'win32/common.c',
			'win32/vigem_gamepad.c',
			'win32/winapi_device.c',
			'win32/keyboard_buttons.c',
		]
	)
	
	platform_dependent_link = [ win32_lib ]
	platform_dependent_deps = [
		meson.get_compiler('c').find_library('regex'),
		meson.get_compiler('c').find_library('wsock32'),
		meson.get_compiler('c').find_library('libusb-1.0'),
	]
endif

executable('scc-daemon',
	include_directories: include,
	link_with: [utils_lib, tools_lib, parser_lib,
				actions_lib, config_lib] + platform_dependent_link,
	dependencies: platform_dependent_deps,
	sources: [
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
