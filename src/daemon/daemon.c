/**
 * SC Controller - Daemon
 */
#define LOG_TAG "Daemon"
#include "scc/utils/traceback.h"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/utils/math.h"
#include "scc/profile.h"
#include "scc/config.h"
#include "scc/mapper.h"
#include "scc/tools.h"
#include "daemon.h"
#include <signal.h>
#include <unistd.h>
#ifndef _WIN32
#include <sys/wait.h>
#endif

static const char* process_name = "scc-daemon";
static LIST_TYPE(sccd_mainloop_cb) mainloop_callbacks;
static LIST_TYPE(SCCDMapper) mappers;
static ControllerList controllers;
static ErrorList errors;

static SCCDMapper* default_mapper = NULL;
static char* default_profile = NULL;
static intptr_t next_error_id = 0;
static bool running = true;
static Client* osd_daemon = NULL;
static Client* autoswitch_daemon = NULL;
static struct { intptr_t osdd; } minions = { -1 };

static void load_default_profile(SCCDMapper* m);
static bool add_mainloop(sccd_mainloop_cb cb);
static void remove_mainloop(sccd_mainloop_cb cb);
static bool controller_add(Controller* c);
static void controller_remove(Controller* c);
static TaskID schedule(uint32_t timeout, sccd_scheduler_cb cb, void* userdata);
static bool sccd_hidapi_enabled();
static void spawn_minions(void* trash1, void* trash2);


static Daemon _daemon = {
	.controller_add				= controller_add,
	.controller_remove			= controller_remove,
	.error_add					= sccd_error_add,
	.error_remove				= sccd_error_remove,
	.mainloop_cb_add			= add_mainloop,
	.mainloop_cb_remove			= remove_mainloop,
	.schedule					= schedule,
	.cancel						= sccd_scheduler_cancel,
	.poller_cb_add				= sccd_poller_add,
	.hotplug_cb_add				= sccd_register_hotplug_cb,
	.get_controller_by_id		= sccd_get_controller_by_id,
	.get_x_display				= sccd_x11_get_display,
	.get_config_path			= scc_get_config_path,
	.get_hidapi_enabled			= sccd_hidapi_enabled,
};

Daemon* get_daemon() {
	return &_daemon;
}


static bool add_mainloop(sccd_mainloop_cb cb) {
	return list_add(mainloop_callbacks, cb);
}

static void remove_mainloop(sccd_mainloop_cb cb) {
	list_remove(mainloop_callbacks, cb);
}

static void schedule_cb(void* cb, void* userdata) {
	((sccd_scheduler_cb)(cb))(userdata);
}

static TaskID schedule(uint32_t timeout, sccd_scheduler_cb cb, void* userdata) {
	return sccd_scheduler_schedule(timeout, &schedule_cb, (void*)cb, userdata);
}

void sccd_exit() {
	running = false;
}

static void sigint_handler(int sig) {
	INFO("^C caught");
	sccd_exit();
}

static bool sccd_hidapi_enabled() {
#if USE_HIDAPI
	return true;
#else
	return false;
#endif
}



/**
 * Returns first available mapper or creates new if all mappers
 * are already used. Available mapper is one with no controller
 * assigned.
 *
 * Returns NULL if allocation fails.
 */
static SCCDMapper* grab_mapper() {
	FOREACH_IN(SCCDMapper*, m, mappers) {
		Mapper* m_ = sccd_mapper_to_mapper(m);
		if (m_->get_controller(m_) == NULL) {
			// Got one
			return m;
		}
	}
	
	// No mappers left
	if (!list_allocate(mappers, 1)) {
		LERROR("Cannot allocate any more mappers (out of memory)");
		return NULL;
	}
	SCCDMapper* m = sccd_mapper_create();
	if (m == NULL) {
		LERROR("Failed to create mapper");
		return NULL;
	}
	
	ASSERT(list_add(mappers, m));
	// TODO: Don't load default for everything, use last
	// TODO: selected profile instead
	load_default_profile(m);
	return m;
}

/** Returns NULL if no mapper has specified controller assigned */
static SCCDMapper* get_mapper_for_controller(Controller* c) {
	ListIterator it = iter_get(mappers);
	FOREACH(SCCDMapper*, m, it) {
		Mapper* m_ = sccd_mapper_to_mapper(m);
		if (m_->get_controller(m_) == c) {
			iter_free(it);
			return m;
		}
	}
	iter_free(it);
	return NULL;
}

const char* get_profile_for_controller(Controller* c) {
	ListIterator it = iter_get(mappers);
	const char* filename = NULL;
	FOREACH(SCCDMapper*, m, it) {
		Mapper* m_ = sccd_mapper_to_mapper(m);
		if (m_->get_controller(m_) == c) {
			filename = sccd_mapper_get_profile_filename(m);
			if (filename == NULL) filename = "None";
			break;
		}
	}
	iter_free(it);
	return filename;
}

static const char* profile_load_error_to_string(int err) {
	switch (err) {
	case 0:
		return "out of memory";
	case 1:
		return "failed to open the file";
	case 2:
		return "failed to decode JSON data";
	case 3:
		return "failed to decode profile";
	}
	return "unknown error";
}

/**
 * Sets proctitle.
 * Allocates memory, parses profile name from path and does all that
 * boring stuff so it's not repeated everywhere.
 */
static void set_proctitle(const char* profile_filename) {
	char* title;
	if (profile_filename == NULL) {
		title = strbuilder_fmt("%s (starting)", process_name);
	} else {
		while (strstr(profile_filename, "/") != NULL)
			profile_filename = strstr(profile_filename, "/") + 1;
		title = strbuilder_fmt("%s (%s)", process_name, profile_filename);
	}
	if (title != NULL) {
		sccd_set_proctitle(title);
		free(title);
	}
}

bool sccd_set_profile(Mapper* m, const char* filename) {
	int err;
	char* message;
	Profile* current = m->get_profile(m);
	Profile* p = scc_profile_from_json(filename, &err);
	SCCDMapper* m_ = sccd_mapper_to_sccd_mapper(m);
	if (m_ != NULL) {
		if (!sccd_mapper_set_profile_filename(m_, filename)) {
			WARN("Failed to load profile (out of memory). Ignoring request.");
			RC_REL(p);
			return false;
		}
	}
	if (p == NULL) {
		WARN("Failed to load profile (%s). Ignoring request.", profile_load_error_to_string(err));
		RC_REL(p);
		return false;
	}
	
	p->compress(p);
	if (sccd_is_locked_profile(current)) {
		sccd_change_locked_profile(current, p);
	} else {
		m->set_profile(m, p, true);
		RC_REL(p);
	}
	if (m == sccd_mapper_to_mapper(default_mapper)) {
		LOG("Activated profile '%s' on default_mapper", filename);
		set_proctitle(filename);
		message = strbuilder_fmt("Current profile: %s\n", filename);
		if (message != NULL) {
			sccd_socket_send_to_all(message);
			free(message);
		}
	} else {
		LOG("Activated profile '%s'", filename);
	}
	if (m->get_controller(m) != NULL) {
		Controller* c = m->get_controller(m);
		message = strbuilder_fmt("Controller profile: %s %s\n", c->get_id(c), filename);
		if (message != NULL) {
			sccd_socket_send_to_all(message);
			free(message);
		}
	}
	// TODO: all of this
	/*
	if mapper.profile.gyro and not p.gyro:
			# Turn off gyro sensor that was enabled but is no longer needed
			if mapper.get_controller():
				log.debug("Turning gyrosensor OFF")
				mapper.get_controller().set_gyro_enabled(False)
		elif not mapper.profile.gyro and p.gyro:
			# Turn on gyro sensor that was turned off, if profile has gyro action set
			if mapper.get_controller():
				log.debug("Turning gyrosensor ON")
				mapper.get_controller().set_gyro_enabled(True)
		# Cancel everything
		mapper.cancel_all()
		# Release all buttons
		mapper.release_virtual_buttons()
		# Reset mouse (issue #222)
		mapper.mouse.reset()
	*/
	
	// TODO:
	/*
	if mapper.get_controller():
		self.send_profile_info(mapper.get_controller(), self._send_to_all)
	else:
		self.send_profile_info(None, self._send_to_all, mapper=mapper)
	*/
	
	return true;
}

const char* sccd_get_current_profile() {
	const char* filename = sccd_mapper_get_profile_filename(default_mapper);
	if (filename == NULL) filename = default_profile;
	if (filename == NULL) filename = "None";
	return filename;
}

static bool controller_add(Controller* c) {
	SCCDMapper* m = NULL;
	// Verify sanity of controller ID
	const char* id = c->get_id(c);
	if (strchr(id, ' ') != NULL) {
		LERROR("Cannot add controller with ID '%s', ID contains space.");
		return false;
	}
	ListIterator it = iter_get(controllers);
	FOREACH(Controller*, c, it) {
		if (strcmp(c->get_id(c), id) == 0) {
			LERROR("Cannot add controller with ID '%s', duplicate ID.");
			iter_free(it);
			return false;
		}
	}
	iter_free(it);
	
	// Allocate & reserve memory
	if (!list_allocate(controllers, 1)) {
		LERROR("Cannot add any more controllers (out of memory)");
		return false;
	}
	if ((m = grab_mapper()) == NULL)
		// grab_mapper logs error message
		return false;
	if (m != default_mapper)
		DEBUG("(Re)using mapper %p for %s", m, c->get_description(c));
	ASSERT(list_add(controllers, c));
	
	// Store & assign mapper
	Mapper* m_ = sccd_mapper_to_mapper(m);
	m_->set_controller(m_, c);
	c->set_mapper(c, m_);
	if (m == default_mapper)
		DEBUG("Assigned default_mapper to %s", c->get_description(c));
	// TODO: Gyros
	// if mapper.profile.gyro:
	// 	log.debug("Turning gyrosensor ON")
	// 	c.set_gyro_enabled(True)
	
	// TODO: Config
	// c.apply_config(Config().get_controller_config(c.get_id()))
	
	LOG("Controller added: %s", c->get_description(c));
	sccd_clients_for_all(sccd_send_controller_list);
	sccd_clients_for_all(sccd_send_profile_list);
	
	return true;
}

static void controller_remove(Controller* c) {
	if (list_remove(controllers, c)) {
		// Controller is known and was removed from controllers list
		SCCDMapper* m = get_mapper_for_controller(c);
		if (m != NULL) {
			Mapper* m_ = sccd_mapper_to_mapper(m);
			m_->set_controller(m_, NULL);
			c->set_mapper(c, NULL);
		}
		LOG("Controller removed: %s", c->get_description(c));
		c->deallocate(c);
		sccd_clients_for_all(sccd_send_controller_list);
		sccd_clients_for_all(sccd_send_profile_list);
	}
}

static void setup_default_mapper() {
	SCCDMapper* m = sccd_mapper_create();
	ASSERT(m != NULL);
	default_mapper = m;
	ASSERT(list_add(mappers, default_mapper));
}

SCCDMapper* sccd_get_default_mapper() {
	return default_mapper;
}

/** Unloads all mappers and default profile */
static void unload_mappers() {
	FOREACH_IN(SCCDMapper*, m, mappers) {
		Mapper* m_ = sccd_mapper_to_mapper(m);
		Controller* c = m_->get_controller(m_);
		m_->set_profile(m_, NULL, true);
		if (c != NULL) c->set_mapper(c, m_);
		sccd_mapper_deallocate(m);
	}
	list_clear(mappers);
	default_mapper = NULL;
}

static void load_default_profile(SCCDMapper* m) {
	if (m == NULL) m = default_mapper;
	if (default_profile == NULL) {
		Config* c = config_load();
		char* recents[1];
		int count = config_get_strings(c, "recent_profiles", (const char**)&recents, 1);
		if ((count >= 1) || (count == -2)) {
			// -2 means more data available. 1st value is still valid in that case
			default_profile = scc_find_profile(recents[0]);
		}
		RC_REL(c);
	}
	
	int err;
	ASSERT(default_profile != NULL);
	Profile* p = scc_profile_from_json(default_profile, &err);
	if (!sccd_mapper_set_profile_filename(m, default_profile)) {
		WARN("Failed to load profile (out of memory). Starting with no mappings.");
		RC_REL(p);
		p = scc_make_empty_profile();
	}
	if (p == NULL) {
		WARN("Failed to load profile (%s). Starting with no mappings.", profile_load_error_to_string(err));
		p = scc_make_empty_profile();
	}
	
	p->compress(p);
	Mapper* m_ = sccd_mapper_to_mapper(m);
	m_->set_profile(m_, p, true);
	RC_REL(p);
	LOG("Activated default profile '%s'", default_profile);
	set_proctitle(default_profile);
}

intptr_t sccd_error_add(const char* message, bool fatal) {
	ErrorData* e = NULL;
	if (!list_allocate(errors, 1))
		goto sccd_error_add_fail;
	if ((e = malloc(sizeof(ErrorList))) == NULL)
		goto sccd_error_add_fail;
	e->fatal = fatal;
	e->id = next_error_id;
	e->message = strbuilder_cpy(message);
	if (e->message == NULL)
		goto sccd_error_add_fail;
	
	list_add(errors, e);
	next_error_id ++;
	if (next_error_id == INTPTR_MAX)
		// This is kinda bad, but improbable.
		next_error_id = 0;
	return e->id;
	
sccd_error_add_fail:
	LERROR("OOM; Failed to add error");
	free(e);
	return -1;
}

static bool _error_remove_filter_fn(void* _e, void* _id) {
	ErrorData* e = (ErrorData*)_e;
	intptr_t id = (intptr_t)_id;
	
	if (e->id == id) {
		free(e->message);
		free(e);
		return false;
	}
	return true;
}

void sccd_error_remove(intptr_t id) {
	list_filter(errors, _error_remove_filter_fn, (void*)id);
}

ErrorList sccd_get_errors() {
	return errors;
}

ControllerList sccd_get_controller_list() {
	return controllers;
}

Controller* sccd_get_controller_by_id(const char* id) {
	FOREACH_IN(Controller*, c, controllers) {
		if (0 == strcmp(c->get_id(c), id))
			return c;
	}
	return NULL;
}

Client* sccd_get_special_client(enum SpecialClientType t) {
	switch (t) {
	case SCT_OSD:
		return osd_daemon;
	case SCT_AUTOSWITCH:
		return autoswitch_daemon;
	default:
		FATAL("Invalid SpecialClientType");
	}
}

void sccd_set_special_client(enum SpecialClientType t, Client* client) {
	Client** target;
	switch (t) {
	case SCT_OSD:
		target = &osd_daemon;
		break;
	case SCT_AUTOSWITCH:
		target = &autoswitch_daemon;
		break;
	default:
		FATAL("Invalid SpecialClientType");
	}
	
	if (*target != NULL) {
		sccd_drop_client_asap(*target);
	}
	*target = client;
}

#ifndef _WIN32
static void store_pid() {
	FILE* f = fopen(scc_get_pid_file(), "w");
	if (f != NULL) {
		fprintf(f, "%i\n", getpid());
		fclose(f);
	} else {
		WARN("Failed to write pid file");
	}
}

/**
 * Removes pidfile _only_ if it still contains my own PID.
 * There is no locking around this so it's not really safe, but should
 * be enough in most cases.
 */
static void remove_pid_file() {
	char r_buffer[256] = {0};
	char m_buffer[256] = {0};
	const char* pid_file = scc_get_pid_file();
	size_t r = 0;
	FILE* f = fopen(pid_file, "r");
	if (f != NULL) {
		r = fread(r_buffer, 1, 255, f);
		fclose(f);
	}
	if (r <= 0) {
		// Failed read PID file, just (try to) remove it as it is
		unlink(pid_file);
	} else {
		// Check whether PID matches my own PID, remove pidfile if it does
		snprintf(m_buffer, 255, "%i\n", getpid());
		if (0 == strcmp(m_buffer, r_buffer)) {
			unlink(pid_file);
		}
	}
}

static void respawn_minion(int sig) {
	int stat;
	pid_t pid = wait(&stat);
	if (pid <= 0) return;
	if (pid == minions.osdd) {
		WARN("scc-osd-daemon died; restarting in 5s...");
		minions.osdd = -1;
		sccd_scheduler_schedule(5000, spawn_minions, NULL, NULL);
	}
}
#endif

/**
 * Starts scc-osd-daemon and scc-autoswitch-daemon
 * and keeps them running if they crash.
 */
static void spawn_minions(void* trash1, void* trash2) {
	if (minions.osdd <= 0) {
		char* osdd = scc_find_binary("scc-osd-daemon");
		if (osdd == NULL) {
			WARN("Cannot start scc-osd-daemon: binary not found");
		} else {
			char* argv[] = { osdd, NULL };
			minions.osdd = scc_spawn(argv, 0);
			free(osdd);
			if (minions.osdd < 0)
				WARN("Cannot start scc-osd-daemon: error %i", minions.osdd);
		}
	}
	// TODO: autoswitch daemon here
}

void sccd_set_default_profile(const char* profile) {
	default_profile = scc_find_profile(profile);
	if (default_profile == NULL)
		WARN("Default profile set from command line not found.");
}


int sccd_start() {
	INFO("Starting SC Controller Daemon v%s...", DAEMON_VERSION);
	set_proctitle(NULL);
	mainloop_callbacks = list_new(sccd_mainloop_cb, 0);
	mappers = list_new(SCCDMapper, 16);
	controllers = list_new(Controller, 16);
	errors = list_new(ErrorData, 16);
	Config* c = config_init();
	if (c == NULL) return 1;
	RC_REL(c);
	
	sccd_scheduler_init();
	sccd_poller_init();
	if (!sccd_socket_init()) {
		LERROR("Failed to create control socket.");
		// Nothing important was open yet, so I can just bail out on this error.
		return 1;
	}
	sccd_device_monitor_init(&_daemon);
#ifdef __BSD__
	sccd_input_bsd_init(&_daemon);
#endif
#ifdef USE_LIBUSB
	sccd_input_libusb_init(&_daemon);
#endif
#ifdef USE_HIDAPI
	sccd_input_hidapi_init(&_daemon);
#endif
#ifdef USE_DINPUT
	sccd_input_dinput_init();
#endif
	sccd_x11_init();
	sccd_drivers_init(&_daemon, DIMODE_ALL);
#ifdef __linux__
	sccd_device_monitor_start(&_daemon);
#endif
	// here: load_custom_module
	setup_default_mapper();
	sccd_cemuhook_socket_enable();
	load_default_profile(NULL);
#ifndef _WIN32
	store_pid();
#endif
	// here: check X server
	spawn_minions(NULL, NULL);
	// here: start_drivers() // needed?
	sccd_device_monitor_rescan(&_daemon);
	
	ListIterator iter = iter_get(mainloop_callbacks);
	if (iter == NULL) {
		LERROR("Failed to allocate memory");
		running = false;
	}
	
	signal(SIGTERM, sigint_handler);
	signal(SIGINT, sigint_handler);
#ifndef _WIN32
	// TODO: how do I get sigchild on Windows?
	signal(SIGCHLD, respawn_minion);
#endif
	INFO("Ready.");
	
	// Mainloop is waiting mostly on sccd_poller_mainloop_cb on Linux or
	// sccd_input_hidapi_mainloop everywhere else.
	// Additionally, to prevent daemon from using CPU doing nothing when
	// there is no controller connected, at most 10ms sleep is added at end of loop
	while (running) {
		monotime_t start = mono_time_ms();
		FOREACH(sccd_mainloop_cb, cb, iter)
			cb(&_daemon);
		list_foreach(mappers, (list_foreach_cb)sccd_mapper_flush);
		iter_reset(iter);
		monotime_t end = mono_time_ms();
		if (end - start < 10)
			usleep((10 - (end - start)) * 1000);
	}
	
	DEBUG("Exiting...");
#ifndef _WIN32
	remove_pid_file();
#endif
	iter_free(iter);
	// here: stop listening
	// here: kill mappers
	// here: kill drivers
	sccd_device_monitor_close();
#ifdef __BSD__
	sccd_input_bsd_close();
#endif
#ifdef USE_LIBUSB
	sccd_input_libusb_close();
#endif
#ifdef USE_HIDAPI
	sccd_input_hidapi_close();
#endif
#ifdef USE_DINPUT
	sccd_input_dinput_close();
#endif
	sccd_poller_close();
	sccd_scheduler_close();
	list_free(mainloop_callbacks);
	unload_mappers();
	return 0;
}

