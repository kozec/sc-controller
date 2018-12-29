add_languages('cpp')

libvigemclient = shared_library('vigemclient',
	include_directories: include_directories('vigemclient/include'),
	dependencies: [
		meson.get_compiler('cpp').find_library('setupapi'),
		meson.get_compiler('cpp').find_library('hid'),
	],
	sources: [ 'vigemclient/ViGEmClient.cpp' ],
)

uinput_lib = static_library('win32',
	include_directories: [include, include_directories('vigemclient/include')],
	link_with: libvigemclient,
	sources: [
		'common.c',
		'vigem_gamepad.c',
		'winapi_device.c',
	]
)
