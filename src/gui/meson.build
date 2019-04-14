platform_dependent_deps = []
platform_dependent_src = []

if host_machine.system() == 'linux'
	platform_dependent_deps = []
	platform_dependent_src = []
elif host_machine.system() == 'openbsd' or host_machine.system() == 'netbsd'
	platform_dependent_deps = []
	platform_dependent_src = []
elif host_machine.system() == 'windows'
	platform_dependent_deps = []
	platform_dependent_src = [
		import('windows').compile_resources('sc-controller.rc')
	]
else
	error('Unsupported system ' + host_machine.system() + ', please add it here')
endif


executable('sc-controller',
	include_directories: include,
	link_with: [ utils_lib, tools_lib ],
	dependencies: platform_dependent_deps + [
		dependency('python-2.7')
	],
	build_rpath: '/usr/X11R6/lib',
	sources: platform_dependent_src + [
		'gui.c',
	],
)

