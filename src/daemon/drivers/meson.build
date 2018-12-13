libc = meson.get_compiler('c').find_library('c')

shared_library('scc_drv_sc_by_cable',
	include_directories: [ include ],
	link_with: [ utils_lib ],
	dependencies: [ libc ],
	sources: [
		'sc/common.c',
		'sc/by_cable.c',
	]
)

shared_library('scc_drv_sc_dongle',
	include_directories: [ include ],
	link_with: [ utils_lib ],
	dependencies: [ libc ],
	sources: [
		'sc/common.c',
		'sc/dongle.c',
	]
)


remotepad_deps = [ libc ]

if host_machine.system() == 'windows'
	remotepad_deps = [
		meson.get_compiler('c').find_library('wsock32'),
	]
endif

shared_library('scc_drv_remotepad',
	include_directories: [ include ],
	link_with: [ utils_lib ],
	dependencies: remotepad_deps,
	sources: [
		'remotepad/remotepad.c',
		'remotepad/remotepad_controller.c',
	]
)
