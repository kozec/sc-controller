libm = meson.get_compiler('c').find_library('m')

if get_option('x11-output').enabled() or host_machine.system() == 'openbsd' or host_machine.system() == 'netbsd'
	virtual_device_lib = shared_library('scc-virtual-device',
		link_with: [ utils_lib, conversions_lib ],
		include_directories: include,
		dependencies: [
			dependency('xtst'),
			dependency('x11'),
			libm,
		],
		sources: [
			'uinput-x11/common.c',
			'uinput-x11/mouse.c',
			'uinput-x11/keyboard.c',
		]
	)
elif host_machine.system() == 'linux'
	virtual_device_lib = shared_library('scc-virtual-device',
		link_with: [ utils_lib, conversions_lib ],
		include_directories: include,
		dependencies: [ libm ],
		sources: [
			'uinput/common.c',
			'uinput/mouse.c',
			'uinput/gamepad.c',
			'uinput/keyboard.c',
		]
	)
elif host_machine.system() == 'windows'
	add_languages('cpp')
	
	libvigemclient = shared_library('vigemclient',
		include_directories: include_directories('uinput-win32/vigemclient/include'),
		dependencies: [
			meson.get_compiler('cpp').find_library('setupapi'),
			meson.get_compiler('cpp').find_library('hid'),
		],
		sources: [ 'uinput-win32/vigemclient/ViGEmClient.cpp' ],
	)
	
	virtual_device_lib = shared_library('scc-virtual-device',
		include_directories: [include, include_directories('uinput-win32/vigemclient/include')],
		link_with: [ utils_lib, conversions_lib, libvigemclient ],
		dependencies: [ libm ],
		sources: [
			'uinput-win32/common.c',
			'uinput-win32/vigem_gamepad.c',
			'uinput-win32/winapi_device.c',
		]
	)
else
	error('Unsupported system ' + host_machine.system() + ', please add it here')
endif

