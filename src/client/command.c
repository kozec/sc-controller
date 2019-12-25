/**
 * SC-Controller - Client - Command
 * 
 * Code for handing some of messages that scc-daemon can send to client
 */

#define LOG_TAG "SCCC"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/tokenizer.h"
#include "scc/utils/iterable.h"
#include "scc/utils/list.h"
#include "scc/client.h"
#include "client.h"

/** Returns 1 if message was parsed and handled, -1 on OOM error */
int on_command(struct _SCCClient* c, char* msg) {
	Tokens* tokens = tokenize(msg);
	if (tokens == NULL) {
		LERROR("OOM error while parsing message. Closing connection");
		return -1;
	}
	tokens_auto_skip_whitespace(tokens);
	const char* command = iter_next(tokens);
	switch (command[0]) {
	// Missing:
	// elif line.startswith("Ready."):
	// elif line.startswith("OK."):
	// elif line.startswith("Fail:"):
	// elif line.startswith("Error:"):
	// elif line.startswith("Current profile:"):
	case '#': {
		// Response (as in "Ok." or "Fail: something") to tagged message
		store_response(c, command, tokens_get_rest(tokens));
		tokens_free(tokens);
		return 1;
	}
	case 'E':
		if (0 == strcmp(command, "Event:")) {
			if (c->client.callbacks.on_event != NULL) {
				const char* cid = iter_next(tokens);
				on_controller_event(c, cid, tokens);
				// on_controller_event frees tokens
				return 1;
			}
			tokens_free(tokens);
			return 0;
		}
		break;
	case 'C':
		if (0 == strcmp(command, "Controller:")) {
			const char* id = iter_next(tokens);
			ControllerData* cd = get_data_by_id(c, id);
			if (cd == NULL) goto on_command_oom;
			cd->type = strbuilder_cpy(iter_next(tokens));
			cd->flags = strtol(iter_next(tokens), NULL, 10);
			cd->config_file = strbuilder_cpy(tokens_get_rest(tokens));
			cd->alive = true;
			tokens_free(tokens);
			return 1;
		}
		if (0 == strcmp(command, "Controller")) {
			command = iter_next(tokens);
			// TODO: "Controller Count" should be "Controller count"
			if (0 == strcmp(command, "Count:")) {
				remove_nonalive(c->controllers);
				list_foreach(c->controllers, &mark_non_alive_foreach_cb);
				if (c->client.callbacks.on_controllers_changed != NULL)
					c->client.callbacks.on_controllers_changed(&c->client, list_len(c->controllers));
				tokens_free(tokens);
				return 1;
			}
			tokens_free(tokens);
			return 0;
		}
		// TODO: "Controller profile:"
		break;
	case 'V':
		if (0 == strcmp(command, "Version:")) {
			const char* version = tokens_get_rest(tokens);
			if (c->client.callbacks.on_version_recieved != NULL)
				c->client.callbacks.on_version_recieved(&c->client, version);
			else
				DDEBUG("Connected to daemon, version %s", version);
			tokens_free(tokens);
			return 1;
		}
		break;
	case 'R':
		if (0 == strcmp(command, "Ready.")) {
			if (c->client.callbacks.on_ready != NULL)
				c->client.callbacks.on_ready(&c->client);
			tokens_free(tokens);
			return 1;
		}
		if (0 == strcmp(command, "Reconfigured.")) {
			if (c->client.callbacks.on_reconfigured != NULL)
				c->client.callbacks.on_reconfigured(&c->client);
			tokens_free(tokens);
			return 1;
		}
		break;
	
	}
	tokens_free(tokens);
	return 0;

on_command_oom:
	tokens_free(tokens);
	return -1;
}

inline static bool add_unqouted(StrBuilder* sb, StringList lst) {
	const char* value = strbuilder_get_value(sb);
	if ((value[0] == '\'') || (value[0] == '"')) {
		if (value[0] == value[strlen(value) - 1]) {
			strbuilder_rtrim(sb, 1);
			strbuilder_ltrim(sb, 1);
		}
	}
	return list_add(lst, strbuilder_consume(sb));
}

StringList sccc_parse(const char* msg) {
	StringList lst = list_new(char, 1);
	StrBuilder* sb = strbuilder_new();
	Tokens* tokens = tokenize(msg);
	if ((lst == NULL) || (tokens == NULL) || (sb == NULL))
		goto sccc_parse_oom;
	// tokens_auto_skip_whitespace(tokens);
	list_set_dealloc_cb(lst, free);
	
	const char* item = iter_next(tokens);
	while (item != NULL) {
		if (!strbuilder_add(sb, item))
			goto sccc_parse_oom;
		// LOG("sccc_parse: [%s] next '%c'", item, tokens_peek_char(tokens));
		if (tokens_peek_char(tokens) == ' ') {
			// LOG("sccc_parse: word");
			if (!add_unqouted(sb, lst)) {
				sb = NULL;
				goto sccc_parse_oom;
			}
			if ((sb = strbuilder_new()) == NULL)
				goto sccc_parse_oom;
			tokens_skip_whitespace(tokens);
		}
		if (!iter_has_next(tokens))
			break;
		item = iter_next(tokens);
	}
	if (strbuilder_len(sb) > 0) {
		if (!add_unqouted(sb, lst)) {
			sb = NULL;
			goto sccc_parse_oom;
		}
		// LOG("sccc_parse: word");
	}
	return lst;
	
sccc_parse_oom:
	tokens_free(tokens);
	strbuilder_free(sb);
	list_free(lst);
	return NULL;
}

