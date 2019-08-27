subdir('common')
subdir('menus')
subdir('keyboard')

executable('scc-osd-menu',
	include_directories: include,
	link_with: [ tools_lib, utils_lib, osd_menu_lib ],
	dependencies: [ dependency('gtk+-3.0', version: '>=3.22.0') ],
	sources: [
		'osd-menu.c',
	],
)

executable('scc-osd-keyboard',
	include_directories: include,
	link_with: [ utils_lib, osd_keyboard_lib ],
	dependencies: [ dependency('gtk+-3.0', version: '>=3.22.0') ],
	sources: [
		'osd-keyboard.c',
	],
)

