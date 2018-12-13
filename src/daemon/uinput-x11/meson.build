uinput_lib = static_library('uinput',
	include_directories: include,
	dependencies: [ meson.get_compiler('c').find_library('Xtst') ],
	sources: [
		'common.c',
		'mouse.c',
		'keyboard.c',
		'keyboard_buttons.c',
	]
)
