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
	shared_library('scc-drv-evdev',
		include_directories: [ include ],
		dependencies: [
			dependency('libevdev'),
			dependency('zlib'),
		],
		link_with: [ utils_lib, tools_lib, config_lib ],
		sources: [
			'generic/common.c',
			'generic/evdev.c',
		]
	)
endif

if host_machine.system() == 'windows'
	shared_library('scc-drv-dinput',
		include_directories: [ include ],
		dependencies: [
			meson.get_compiler('c').find_library('dinput8'),
			meson.get_compiler('c').find_library('dxguid'),
			dependency('zlib'),
		],
		link_with: [ utils_lib, tools_lib, config_lib ],
		sources: [
			'generic/common.c',
			'generic/dinput.c',
		]
	)
endif

