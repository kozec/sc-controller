platform_dependent_deps = []
if host_machine.system() == 'windows'
	platform_dependent_deps = [
		meson.get_compiler('c').find_library('wsock32'),
	]
endif

client_lib = static_library('scc-client',
	include_directories: include,
	link_with: [ tools_lib, utils_lib ],
	dependencies: platform_dependent_deps,
	sources: [
		'slave_mapper.c',
		'controller.c',
		'command.c',
		'socket.c',
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

