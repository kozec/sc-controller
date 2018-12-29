if host_machine.system() == 'windows'
	deps = []
	remotepad_deps = [
		meson.get_compiler('c').find_library('wsock32'),
	]
else
	libc = meson.get_compiler('c').find_library('c')
	deps = [ libc ]
	remotepad_deps = [ libc ]
endif


shared_library('scc-drv-sc_by_cable',
	include_directories: [ include ],
	link_with: [ utils_lib, config_lib ],
	dependencies: deps,
	sources: [
		'sc/common.c',
		'sc/by_cable.c',
	]
)

shared_library('scc-drv-sc_dongle',
	include_directories: [ include ],
	link_with: [ utils_lib, config_lib ],
	dependencies: deps,
	sources: [
		'sc/common.c',
		'sc/dongle.c',
	]
)

shared_library('scc-drv-remotepad',
	include_directories: [ include ],
	link_with: [ utils_lib ],
	dependencies: remotepad_deps,
	sources: [
		'remotepad/remotepad.c',
		'remotepad/remotepad_controller.c',
	]
)
