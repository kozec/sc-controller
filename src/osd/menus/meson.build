osd_menu_lib = shared_library('scc-osd-menu',
	include_directories: include,
	link_with: [ osd_lib, utils_lib, client_lib, config_lib, gio_client_lib,
				 slave_mapper_lib, virtual_device_lib, tools_lib, actions_lib,
				 parser_lib ],
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

common_deps = [ dependency('gtk+-3.0', version: '>=3.22.0') ]
common_link = [ osd_lib, actions_lib, utils_lib, tools_lib, osd_menu_lib ]


osd_menu_vmenu_lib = shared_library('scc-osd-menu-vmenu',
	include_directories: include,
	link_with: common_link,
	dependencies: common_deps,
	sources: [ 'vmenu.c' ],
)


osd_menu_hmenu_lib = shared_library('scc-osd-menu-hmenu',
	include_directories: include,
	link_with: common_link,
	dependencies: common_deps,
	sources: [ 'hmenu.c' ],
)


radial_deps = [ meson.get_compiler('c').find_library('m') ]

if host_machine.system() == 'linux'
	radial_deps += [
		dependency('x11'),
		dependency('xext'),
	]
endif

osd_menu_radial_menu_lib = shared_library('scc-osd-menu-radialmenu',
	include_directories: include,
	link_with: common_link + [ config_lib ],
	dependencies: common_deps + radial_deps,
	sources: [ 'radial_menu.c' ],
)


osd_menu_grid_menu_lib = shared_library('scc-osd-menu-gridmenu',
	include_directories: include,
	link_with: common_link + [ parser_lib ],
	dependencies: common_deps + [ meson.get_compiler('c').find_library('m') ],
	sources: [ 'grid_menu.c' ],
)

