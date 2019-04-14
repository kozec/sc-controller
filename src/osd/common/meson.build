platform_dependent_deps = []

if host_machine.system() == 'linux'
	platform_dependent_deps = [
		dependency('x11'),
		dependency('xfixes'),
	]
endif


osd_lib = shared_library('scc-osd',
	include_directories: include,
	link_with: [ utils_lib, tools_lib, config_lib, gio_client_lib ],
	c_args: ['-Wno-deprecated-declarations'],
	dependencies: [
		dependency('gtk+-3.0', version: '>=3.22.0'),
		# dependency('glib-2.0', version: '>=2.56.0'),
		
		# TODO: Re-enable cairo & gio for OSK
		# meson.get_compiler('c').find_library('cairo', dirs: ['/usr/local/lib']),
		# meson.get_compiler('c').find_library('gio-2.0', dirs: ['/usr/local/lib']),
	] + platform_dependent_deps,
	sources: [
		'css_magic.c',
		'window.c',
		'icon.c',
	]
)

