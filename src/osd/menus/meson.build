osd_menu_lib = shared_library('scc-osd-menu',
	include_directories: include,
	link_with: [ osd_lib, utils_lib, client_lib, config_lib, gio_client_lib,
				 slave_mapper_lib, tools_lib, actions_lib, parser_lib ],
	c_args: ['-Wno-deprecated-declarations'],
	dependencies: [
		dependency('gtk+-3.0', version: '>=3.22.0'),
		dependency('glib-2.0', version: '>=2.56.0'),
		dependency('gdk-pixbuf-2.0', version: '>=2.0'),
	],
	sources: [
		'menu.c',
		'stick_controller.c',
	]
)

