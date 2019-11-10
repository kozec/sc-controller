platform_dependent_deps = []
platform_dependent_src = []
platform_dependent_link_args = []

if host_machine.system() == 'linux'
	platform_dependent_deps = []
	platform_dependent_src = []
elif host_machine.system() == 'openbsd' or host_machine.system() == 'netbsd'
	platform_dependent_deps = []
	platform_dependent_src = []
elif host_machine.system() == 'windows'
	platform_dependent_deps = []
	platform_dependent_link_args += [ '-mwindows' ]
	platform_dependent_src = [
		import('windows').compile_resources('sc-controller.rc')
	]
else
	error('Unsupported system ' + host_machine.system() + ', please add it here')
endif


sc_controller = executable('sc-controller',
	include_directories: include,
	link_with: [ utils_lib, tools_lib ],
	link_args: platform_dependent_link_args,
	dependencies: platform_dependent_deps + [
		dependency('python-2.7')
	],
	build_rpath: '/usr/X11R6/lib',
	sources: platform_dependent_src + [
		'gui.c',
	],
)


run_target('sc-controller', command: ['sh', '../../meson-run.sh', 'src/gui/sc-controller.exe'],
	dependencies: [sc_controller])

