platform_dependent_deps = []

if host_machine.system() == 'linux'
	platform_dependent_deps = [
		dependency('x11'),
		dependency('xfixes'),
		# dependency('gio-unix-2.0', version: '>=2.20')
	]
endif


osd_lib = static_library('osd',
	include_directories: include,
	link_with: [ utils_lib, tools_lib, config_lib, gio_client_lib ],
	c_args: ['-Wno-deprecated-declarations'],
	dependencies: [
		dependency('gtk+-3.0', version: '>=3.22.0'),
		dependency('glib-2.0', version: '>=2.56.0'),
		
		# TODO: Re-enable cairo & gio for OSK
		# meson.get_compiler('c').find_library('cairo', dirs: ['/usr/local/lib']),
		# meson.get_compiler('c').find_library('gio-2.0', dirs: ['/usr/local/lib']),
	] + platform_dependent_deps,
	sources: [
		'stick_controller.c',
		'css_magic.c',
		'osd_window.c',
		'osd_menu.c',
	]
)


executable('scc-osd-menu',
	include_directories: include,
	link_with: [ osd_lib, actions_lib, parser_lib ],
	dependencies: [
		dependency('gtk+-3.0', version: '>=3.22.0'),
	],
	sources: [
		'menu.c',
	],
)

