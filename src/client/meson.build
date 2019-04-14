platform_dependent_deps = []
platform_dependent_link_with = []

if host_machine.system() == 'windows'
	msys_socket_lib = shared_library('msys_socket',
		include_directories: include,
		link_with: [utils_lib],
		dependencies: [ meson.get_compiler('c').find_library('wsock32') ],
		sources: [ '../utils/msys_socket.c', ]
	)
	
	platform_dependent_deps = [
		meson.get_compiler('c').find_library('wsock32'),
	]
	platform_dependent_link_with = [
		msys_socket_lib,
	]
endif

client_lib = shared_library('scc-client',
	include_directories: include,
	link_with: [ tools_lib, utils_lib ] + platform_dependent_link_with,
	dependencies: platform_dependent_deps,
	sources: [
		'controller.c',
		'command.c',
		'socket.c',
	]
)

slave_mapper_lib = shared_library('scc-slave-mapper',
	include_directories: include,
	link_with: [utils_lib, tools_lib, client_lib, virtual_device_lib ],
	sources: [
		'slave_mapper.c',
	]
)

gio_client_lib = shared_library('scc-gio-client',
	include_directories: include,
	link_with: [ client_lib ],
	c_args: ['-Wno-deprecated-declarations'],
	dependencies: [
		dependency('glib-2.0', version: '>=2.56.0'),
	],
	sources: [
		'gio.c',
	]
)

