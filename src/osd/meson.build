subdir('common')
subdir('menus')
subdir('keyboard')

scc_osd_menu = executable('scc-osd-menu',
	include_directories: include,
	link_with: [ tools_lib, utils_lib, osd_menu_lib ],
	dependencies: [ dependency('gtk+-3.0', version: '>=3.22.0') ],
	sources: [
		'osd-menu.c',
	],
)

scc_osd_keyboard = executable('scc-osd-keyboard',
	include_directories: include,
	link_with: [ utils_lib, osd_keyboard_lib ],
	dependencies: [ dependency('gtk+-3.0', version: '>=3.22.0') ],
	sources: [
		'osd-keyboard.c',
	],
)


run_target('scc-osd-menu', command: ['sh', '../../../meson-run.sh', 'src/osd/scc-osd-menu.exe', '-f', '/e/SC Controller/share/default_menus/Default.menu'],
	dependencies: [scc_osd_menu])

