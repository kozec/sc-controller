subdir('common')
subdir('menus')
subdir('keyboard')

scc_osd_daemon = executable('scc-osd-daemon',
	include_directories: include,
	link_with: [ tools_lib, utils_lib, osd_menu_lib, osd_keyboard_lib,
					config_lib, client_lib, gio_client_lib ],
	dependencies: [ dependency('gtk+-3.0', version: '>=3.22.0') ],
	sources: [
		'osd-daemon.c',
	],
)

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


run_target('scc-osd-menu',
	command: [
		scc_osd_menu,
		'-f', meson.source_root() / 'share' / 'default_menus' / 'Default.menu',
		'-t', 'radial',
		'-c', 'LEFT',
	],
	depends: [scc_osd_menu],
	env: run_target_env,
)


run_target('scc-osd-daemon',
	command: [scc_osd_daemon],
	depends: [scc_osd_daemon],
	env: run_target_env,
)

