deps = []

if host_machine.system() != 'windows'
	libc = meson.get_compiler('c').find_library('c')
	deps = [ libc ]
endif


shared_library('scc-menugen-recent',
	include_directories: [ include ],
	link_with: [ config_lib, actions_lib, bindings_lib ],
	dependencies: deps,
	sources: [ 'recent.c' ]
)

shared_library('scc-menugen-profiles',
	include_directories: [ include ],
	link_with: [ utils_lib, actions_lib, bindings_lib ],
	dependencies: deps,
	sources: [ 'profiles.c' ]
)

