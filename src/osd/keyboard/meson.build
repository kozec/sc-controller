platform_dependent_deps = []

if host_machine.system() != 'windows'
	platform_dependent_deps = [
		dependency('x11'),
	]
endif


osd_keyboard_lib = shared_library('scc-osd-keyboard',
	include_directories: include,
	link_with: [ osd_lib, utils_lib, tools_lib, client_lib, config_lib,
				 slave_mapper_lib, virtual_device_lib, gio_client_lib,
				 conversions_lib, actions_lib, parser_lib ],
	c_args: ['-Wno-deprecated-declarations'],
	dependencies: [
		dependency('gtk+-3.0', version: '>=3.22.0'),
		dependency('glib-2.0', version: '>=2.56.0'),
		dependency('gdk-pixbuf-2.0', version: '>=2.0'),
	] + platform_dependent_deps,
	sources: [
		'init.c',
		'data.c',
		'actions.c',
		'display.c',
	]
)

