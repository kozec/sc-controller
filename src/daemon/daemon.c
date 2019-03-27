/**
 * SC Controller - Daemon - main module
 *
 * Here is where everything starts
 */
#define LOG_TAG "Daemon"
#include "scc/utils/traceback.h"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/profile.h"
#include "scc/config.h"
#include "scc/mapper.h"
#include "scc/tools.h"
#include "daemon.h"
#include <signal.h>

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

static void load_default_profile(SCCDMapper* m);
static bool add_mainloop(sccd_mainloop_cb cb);
static void remove_mainloop(sccd_mainloop_cb cb);
static bool controller_add(Controller* c);
static void controller_remove(Controller* c);
static bool schedule(uint32_t timeout, sccd_scheduler_cb cb, void* userdata);


static Daemon _daemon = {
	.controller_add				= controller_add,
	.controller_remove			= controller_remove,
	.error_add					= sccd_error_add,
	.error_remove				= sccd_error_remove,
	.mainloop_cb_add			= add_mainloop,
	.mainloop_cb_remove			= remove_mainloop,
	.schedule					= schedule,
	.poller_cb_add				= sccd_poller_add,
	.hotplug_cb_add				= sccd_register_hotplug_cb,
	.get_x_display				= sccd_x11_get_display,
	.get_usb_helper				= sccd_get_usb_helper,
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

static bool schedule(uint32_t timeout, sccd_scheduler_cb cb, void* userdata) {
	TaskID id = sccd_scheduler_schedule(timeout, &schedule_cb, (void*)cb, userdata);
	return (id != 0);
}


static void sigint_handler(int sig) {
	INFO("^C caught");
	running = false;
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

bool sccd_set_profile(Mapper* m, const char* filename) {
	int err;
	Profile* current = m->get_profile(m);
	Profile* p = scc_profile_from_json(filename, &err);
	if (p == NULL) {
		WARN("Failed to load profile (%s). Ignoring request.", profile_load_error_to_string(err));
		return false;
	}
	
	p->compress(p);
	if (sccd_is_locked_profile(current)) {
		sccd_change_locked_profile(current, p);
	} else {
		m->set_profile(m, p, true);
		RC_REL(p);
	}
	LOG("Activated profile '%s'", filename);
	return true;
	
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
		DEBUG("Reusing mapper %p for %s", m, c->get_description(c));
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
	// TODO: this:
	// self.send_controller_list(self._send_to_all)
	// self.send_all_profiles(self._send_to_all)	
	
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
		// TODO: self.default_profile = find_profile(Config()["recent_profiles"][0])
		// TODO: find_profile function
		Config* c = config_load();
		char* recents[1];
		if (config_get_strings(c, "recent_profiles", (const char**)&recents, 1) >= 1)
			default_profile = scc_find_profile(recents[0]);
		RC_REL(c);
	}
	
	int err;
	Profile* p = scc_profile_from_json(default_profile, &err);
	if (p == NULL) {
		WARN("Failed to load profile (%s). Starting with no mappings.", profile_load_error_to_string(err));
		p = scc_make_empty_profile();
	}
	
	p->compress(p);
	Mapper* m_ = sccd_mapper_to_mapper(m);
	m_->set_profile(m_, p, true);
	RC_REL(p);
	LOG("Activated profile '%s'", default_profile);
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


int main(int argc, char** argv) {
	INFO("Starting SC Controller Daemon v%s...", DAEMON_VERSION);
	traceback_set_argv0(argv[0]);
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
	sccd_usb_helper_init(&_daemon);
	sccd_x11_init();
	sccd_drivers_init(&_daemon);
#ifdef __linux__
	sccd_device_monitor_start(&_daemon);
#endif
	// here: load_custom_module
	setup_default_mapper();
	load_default_profile(NULL);
	// here: load default profile
	// here: start_listening()
	// here: check X server
	// here: start_drivers() // needed?
	sccd_device_monitor_rescan(&_daemon);
	
	ListIterator iter = iter_get(mainloop_callbacks);
	if (iter == NULL) {
		LERROR("Failed to allocate memory");
		running = false;
	}

	signal(SIGTERM, sigint_handler);
	signal(SIGINT, sigint_handler);
	INFO("Ready.");
	
	// Mainloop is timed mostly by sccd_poller_mainloop_cb, as timeout used
	// there is what's keeping thread busy for most time.
	// On windows, sccd_usb_helper_mainloop fullfills same side-effect.
	while (running) {
		FOREACH(sccd_mainloop_cb, cb, iter)
			cb(&_daemon);
		list_foreach(mappers, (list_foreach_cb)sccd_mapper_flush);
		iter_reset(iter);
	}
	
	DEBUG("Exiting...");
	iter_free(iter);
	// here: stop listening
	// here: kill mappers
	// here: kill drivers
	sccd_device_monitor_close();
	sccd_usb_helper_close();
	sccd_poller_close();
	sccd_scheduler_close();
	list_free(mainloop_callbacks);
	unload_mappers();
	return 0;
}
