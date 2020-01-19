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

shared_library('scc-drv-fake',
	include_directories: [ include ],
	link_with: [ utils_lib ],
	sources: [
		'fake/fake.c',
		'fake/fake_controller.c',
	]
)

if host_machine.system() == 'linux'
	shared_library('scc-drv-udev',
		include_directories: [ include ],
		dependencies: [ dependency('libevdev') ],
		link_with: [ utils_lib ],
		sources: [
			'generic/evdev.c',
		]
	)
endif

