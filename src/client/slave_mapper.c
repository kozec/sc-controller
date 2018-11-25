/**
 * SC-Controller - Client - Slave Mapper
 * 
 * Slave mapper... right now... does almost nothing :)
 * If used with SAProfileAction or SATurnoffAction, it forwads request to daemon.
 */

// TODO: Almost everything here

#define LOG_TAG "SCCC"
#include "scc/utils/logging.h"
#include "scc/utils/container_of.h"
#include "scc/utils/strbuilder.h"
#include "scc/special_action.h"
#include "scc/mapper.h"
#include "client.h"

struct SlaveMapper {
	Mapper				mapper;
	ControllerFlags		c_flags;
	SCCClient*			client;
};


static bool special_action(Mapper* _m, unsigned int sa_action_type, void* sa_data) {
	struct SlaveMapper* m = container_of(_m, struct SlaveMapper, mapper);
	if (sa_action_type == SAT_PROFILE) {
		char* command = strbuilder_fmt("Profile: %s", sa_data);
		if (command == NULL) {
			LERROR("Failed to send SAT_PROFILE: Out of memory");
			return true;
		}
		int32_t rid = sccc_request(m->client, command);
		free(command);
		if (rid < 0) {
			LERROR("Failed to send SAT_PROFILE: sccc_request failed");
			return true;
		}
		free(sccc_get_response(m->client, rid));
		return true;
	} else if (sa_action_type == SAT_TURNOFF) {
		int32_t rid = sccc_request(m->client, "Turnoff.");
		// TODO: This is documented worngly
		if (rid < 0) {
			LERROR("Failed to send SAT_TURNOFF: sccc_request failed");
			return true;
		}
		free(sccc_get_response(m->client, rid));
		return true;
	}
	return false;
}

Mapper* sccc_create_slave_mapper(SCCClient* c) {
	struct SlaveMapper* m = malloc(sizeof(struct SlaveMapper));
	if (m == NULL) return NULL;
	memset(m, 0, sizeof(struct SlaveMapper));
	
	// TODO: All of this. Right now it can wotk only with OSD menu
	m->client = c;
	m->c_flags = 0;
	m->mapper.get_flags = NULL;
	m->mapper.set_profile = NULL;
	m->mapper.get_profile = NULL;
	m->mapper.set_controller = NULL;
	m->mapper.get_controller = NULL;
	m->mapper.set_axis = NULL;
	m->mapper.move_mouse = NULL;
	m->mapper.move_wheel = NULL;
	m->mapper.key_press = NULL;
	m->mapper.key_release = NULL;
	m->mapper.is_touched = NULL;
	m->mapper.was_touched = NULL;
	m->mapper.is_pressed = NULL;
	m->mapper.was_pressed = NULL;
	m->mapper.release_virtual_buttons = NULL;
	m->mapper.reset_gyros = NULL;
	m->mapper.special_action = &special_action;
	m->mapper.haptic_effect = NULL;
	m->mapper.schedule = NULL;
	m->mapper.cancel = NULL;
	m->mapper.input = NULL;
	return &m->mapper;
}
