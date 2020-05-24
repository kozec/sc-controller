deps = [ dependency('python-2.7') ]
link = [ utils_lib, tools_lib ]
sources = [ 'gui.c' ]
link_args = []

if host_machine.system() == 'linux'
	# pass
elif host_machine.system() == 'openbsd' or host_machine.system() == 'netbsd'
	# pass
elif host_machine.system() == 'windows'
	link_args += [ '-mwindows' ]
	sources += [
		import('windows').compile_resources('sc-controller.rc')
	]
else
	error('Unsupported system ' + host_machine.system() + ', please add it here')
endif


sc_controller = executable('sc-controller',
	include_directories: include,
	build_rpath: '/usr/X11R6/lib',
	link_args: link_args,
	dependencies: deps,
	sources: sources,
	link_with: link,
)

if host_machine.system() == 'windows'
	# Windows-only 'stay attached to console' executable
	sc_controller_console = executable('sc-controller-console',
		include_directories: include,
		build_rpath: '/usr/X11R6/lib',
		c_args: [ '-DFORCE_CONSOLE' ],
		dependencies: deps,
		sources: sources,
		link_with: link,
	)
endif

run_target('sc-controller',
	command: ['sh', '../../meson-run.sh', 'src/gui/sc-controller'],
	dependencies: [sc_controller])

