/**
 * SC-Controller - Daemon - commands
 * 
 * Handes commands sent from client to daemon
 */

#define LOG_TAG "Daemon"
#include "scc/utils/logging.h"
#include "scc/utils/tokenizer.h"
#include "scc/utils/iterable.h"
#include "scc/tools.h"
#include "daemon.h"

typedef struct Client Client;

/** Shortcut. Sends "OK." to client AND deallocates tokens used to parse its message */
static inline void send_ok(Client* client, Tokens* tokens);

/**
 * Shortcut. Sends message to client AND deallocates tokens used to parse message.
 * Drops client if message is NULL.
 */
static inline void send_error(Client* client, Tokens* tokens, const char* error);

/** As send_error, but deallocates error as well. Drops client if error is NULL */
static inline void send_error_dealoc(Client* client, Tokens* tokens, char* error);

/**
 * Used in really bad case of OOM error, when dropping client is all that daemon
 * can done to recover.
 */
static inline void sccd_on_client_command_oom(Client* client) {
	LERROR("OOM while parsing client message; dropping client");
	sccd_drop_client_asap(client);
}


void sccd_on_client_command(Client* client, char* buffer, size_t len) {
	Tokens* tokens = tokenize(buffer);
	if (tokens == NULL)
		return sccd_on_client_command_oom(client);
	
	tokens_auto_skip_whitespace(tokens);
	const char* command = iter_next(tokens);
	if (client->tag != NULL)
		free(client->tag);
	client->tag = NULL;
	if (command[0] == '#') {
		// Tag recieved
		client->tag = strbuilder_cpy(command);
		if (client->tag == NULL)
			return sccd_on_client_command_oom(client);
		command = iter_next(tokens);
	}
	
	switch (command[0]) {
	case 'B':
		if (0 == strcmp(command, "Button:")) {
			// Emulates pressing or reelasing button on n-th gamepad
			Keycode b = atoi(iter_next(tokens));
			int pressed = atoi(iter_next(tokens));
			if (b == 0)
				return send_error(client, tokens, "Fail: invalid keycode\n");
			if (pressed) {
				if (!client->mapper->is_virtual_key_pressed(client->mapper, b))
					client->mapper->key_press(client->mapper, b, false);
			} else {
				if (client->mapper->is_virtual_key_pressed(client->mapper, b))
					client->mapper->key_release(client->mapper, b);
			}
			return send_ok(client, tokens);
		}
		break;
	case 'C':
		if (0 == strcmp(command, "Controller.")) {
			// Resets controller chosen by client back to default
			// client.mapper = self.default_mapper
			return send_ok(client, tokens);
		}
		if (0 == strcmp(command, "Controller:")) {
			// Assigns controller with given ID to client
			const char* id = iter_next(tokens);
			ListIterator it = iter_get(sccd_get_controller_list());
			FOREACH(Controller*, c, it) {
				if (strcmp(c->get_id(c), id) == 0) {
					iter_free(it);
					// TODO: Actually do something
					// client.mapper = c.get_mapper()
					return send_ok(client, tokens);
				}
			}
			iter_free(it);
			return send_error(client, tokens, "Fail: no such controller\n");
		}
		break;
	case 'E':
		if (0 == strcmp(command, "Exit.")) {
			// Shuts down daemon
			LOG("Exit command recieved.");	
			sccd_exit();
			return send_ok(client, tokens);
		}
	case 'L':
		if (0 == strcmp(command, "Lock:")) {
			// Generates list of sources and attempts to lock them
			StringList sources = list_new(char, 0);
			list_set_dealloc_cb(sources, &free);
			if (sources == NULL)
				return sccd_on_client_command_oom(client);
			while (iter_has_next(tokens)) {
				char* source = strbuilder_cpy(iter_next(tokens));
				bool added = (source != NULL) ? list_add(sources, source) : false;
				if (!added) {
					free(source);
					list_free(sources);
					return sccd_on_client_command_oom(client);
				}
			}
			const char* failed = sccd_lock_actions(client, sources);
			if (failed == SCCD_OOM)
				sccd_on_client_command_oom(client);
			else if (failed == NULL)
				send_ok(client, tokens);
			else
				send_error_dealoc(client, tokens, strbuilder_fmt("Fail: Cannot lock %s\n", failed));
			list_free(sources);
			return;
		} else if (0 == strcmp(command, "Log.")) {
			const char* log = sccd_logger_get_log();
			const char* end = log + strlen(log);
			while (log < end) {
				char* line = NULL;
				const char* next = strstr(log, "\n");
				if (next == NULL) {
					line = malloc(strlen(log) + 7);
					if (line == NULL) return;
					strcpy(line, "Log: ");
					strcat(line, log);
					log = end;
				} else {
					line = malloc(next - log + 1 + 7);
					strcpy(line, "Log: ");
					strncat(line, log, next-log);
					log = next + 1;
				}
				strcat(line, "\n");
				sccd_socket_send(client, line);
				free(line);
			}
			if (!sccd_logger_client_add(client))
				sccd_drop_client_asap(client);	// OOM
			return;
		}
		break;
	case 'O':
		if (0 == strcmp(command, "Observe:")) {
			// TODO: This
			send_error(client, tokens, "Fail: Sniffing disabled.\n");
			return;
		}
		break;
	case 'P':
		if (0 == strcmp(command, "Profile:")) {
			const char* name = tokens_get_rest(tokens);
			char* filename = NULL;
#ifdef _WIN32
			// it's not a problem to overwrite this specific bit of memory here
			scc_path_fix_slashes((char*)name);
#endif
			if (strstr(name, "/") == NULL) {
				// If there is no slash in path, string is treat as profile name
				filename = scc_find_profile(name);
				if (filename == NULL)
					return send_error_dealoc(client, tokens, strbuilder_fmt("Fail: Profile '%s' not found\n", name));
				name = filename;
			}
			LOG("Activating profile '%s'", name);
			if (sccd_set_profile(client->mapper, name))
				send_ok(client, tokens);
			else
				send_error_dealoc(client, tokens, strbuilder_fmt("Fail: Failed to activate profile\n"));
			free(filename);
			return;
		}
		break;
	case 'R':
		if (0 == strcmp(command, "Reconfigure.")) {
			// // Load config
			// cfg = Config()
			// TODO: Reconfigure connected controllers
			// TODO: Start or stop scc-autoswitch-daemon as needed
			// Respond
			send_ok(client, tokens);
			sccd_socket_send_to_all("Reconfigured.\n");
			return;
		}
		if (0 == strcmp(command, "Register:")) {
			const char* as_what = iter_next(tokens);
			if (0 == strcmp(as_what, "osd")) {
				sccd_set_special_client(SCT_OSD, client);
				INFO("Registered scc-osd-daemon");
			} else if (0 == strcmp(as_what, "autoswitch")) {
				sccd_set_special_client(SCT_OSD, client);
				INFO("Registered scc-autoswitch-daemon");
			} else {
				return send_error(client, tokens, "Fail: unknown type\n");
			}
			return send_ok(client, tokens);
		}
		if (0 == strcmp(command, "Rescan.")) {
			INFO("Re-scanning available controllers");
			send_ok(client, tokens);
			sccd_device_monitor_rescan();
			return;
		}
		break;
	case 'T':
		if (0 == strcmp(command, "Turnoff.")) {
			Controller* c = client->mapper->get_controller(client->mapper);
			if (c->turnoff == NULL) {
				WARN("Asked to turn off %s but controller doesn't support this",
							c->get_description(c));
			} else {
				DEBUG("Turning off %s", c->get_description(c));
				c->turnoff(c);
			}
			return send_ok(client, tokens);
		}
		break;
	case 'U':
		if (0 == strcmp(command, "Unlock.")) {
			sccd_unlock_actions(client);
			return send_ok(client, tokens);
		}
		break;
	default:
		break;
	}
	
	// TODO: All of this shit
	/*
	if message.startswith("Profile:"):
		with self.lock:
			try:
				filename = message[8:].decode("utf-8").strip("\t ")
				self._set_profile(client.mapper, filename)
				log.info("Loaded profile '%s'", filename)
				client.wfile.write(b"OK.\n")
			except Exception, e:
				exc = traceback.format_exc()
				log.exception(e)
				tb = unicode(exc).encode("utf-8").encode('string_escape')
				client.wfile.write(b"Fail: " + tb + b"\n")
	elif message.startswith("OSD:"):
		if not self.osd_daemon:
			client.wfile.write(b"Fail: Cannot show OSD; there is no scc-osd-daemon registered\n")
		else:
			try:
				text = message[5:].decode("utf-8").strip("\t ")
				with self.lock:
					if not self._osd("message", text):
						raise Exception()
				client.wfile.write(b"OK.\n")
			except Exception:
				client.wfile.write(b"Fail: cannot display OSD\n")
	elif message.startswith("Feedback:"):
		try:
			position, amplitude = message[9:].strip().split(" ", 2)
			data = HapticData(
				getattr(HapticPos, position.strip(" \t\r")),
				int(amplitude)
			)
			if client.mapper.get_controller():
				client.mapper.get_controller().feedback(data)
			client.wfile.write(b"OK.\n")
		except Exception, e:
			log.exception(e)
			client.wfile.write(b"Fail: %s\n" % (e,))

	elif message.startswith("State."):
		if Config()["enable_sniffing"]:
			client.wfile.write(b"State: %s\n" % (str(client.mapper.state), ))
		else:
			log.warning("Refused 'State' request: Sniffing disabled")
			client.wfile.write(b"Fail: Sniffing disabled.\n")
	elif message.startswith("Led:"):
		try:
			number = int(message[4:])
			number = clamp(0, number, 100)
		except Exception, e:
			client.wfile.write(b"Fail: %s\n" % (e,))
			return
		if client.mapper.get_controller():
			client.mapper.get_controller().set_led_level(number)
	elif message.startswith("Observe:"):
		if Config()["enable_sniffing"]:
			to_observe = [ x for x in message.split(":", 1)[1].strip(" \t\r").split(" ") ]
			with self.lock:
				for l in to_observe:
					client.observe_action(self, SCCDaemon.source_to_constant(l))
				client.wfile.write(b"OK.\n")
		else:
			log.warning("Refused 'Observe' request: Sniffing disabled")
			client.wfile.write(b"Fail: Sniffing disabled.\n")
	elif message.startswith("Replace:"):
		try:
			l, actionstr = message.split(":", 1)[1].strip(" \t\r").split(" ", 1)
			action = TalkingActionParser().restart(actionstr).parse().compress()
		except Exception, e:
			e = unicode(e).encode("utf-8").encode('string_escape')
			client.wfile.write(b"Fail: failed to parse: " + e + "\n")
			return
		with self.lock:
			try:
				if not self._can_lock_action(client.mapper, SCCDaemon.source_to_constant(l)):
					client.wfile.write(b"Fail: Cannot lock " + l.encode("utf-8") + b"\n")
					return
			except ValueError, e:
				tb = unicode(traceback.format_exc()).encode("utf-8").encode('string_escape')
				client.wfile.write(b"Fail: " + tb + b"\n")
				return
			client.replace_action(self, SCCDaemon.source_to_constant(l), action)
			client.wfile.write(b"OK.\n")
	elif message.startswith("Lock:"):
		to_lock = [ x for x in message.split(":", 1)[1].strip(" \t\r").split(" ") ]
		with self.lock:
			try:
				for l in to_lock:
					if not self._can_lock_action(client.mapper, SCCDaemon.source_to_constant(l)):
						client.wfile.write(b"Fail: Cannot lock " + l.encode("utf-8") + b"\n")
						return
			except ValueError, e:
				tb = unicode(traceback.format_exc()).encode("utf-8").encode('string_escape')
				client.wfile.write(b"Fail: " + tb + b"\n")
				return
			for l in to_lock:
				client.lock_action(self, SCCDaemon.source_to_constant(l))
			client.wfile.write(b"OK.\n")
	elif message.startswith("Unlock."):
		with self.lock:
			client.unlock_actions(self)
			client.wfile.write(b"OK.\n")
	elif message.startswith("Rescan."):
		cbs = []
		with self.lock:
			cbs += self.rescan_cbs
			# Respond first
			try:
				client.wfile.write(b"OK.\n")
			except:
				pass
		# Do stuff later
		# (this cannot be done while self.lock is held, as creating new
		# controller would create race condition)
		for cb in self.rescan_cbs:
			try:
				cb()
			except Exception, e:
				log.exception(e)
		# dev_monitor rescan has to be last to run
		try:
			self.dev_monitor.rescan()
		except Exception, e:
			log.exception(e)

	elif message.startswith("Turnoff."):
		with self.lock:
			if client.mapper.get_controller():
				client.mapper.get_controller().turnoff()
			else:
				for c in self.controllers:
					c.turnoff()
			client.wfile.write(b"OK.\n")
	elif message.startswith("Gesture:"):
		try:
			what, up_angle = message[8:].strip().split(" ", 2)
			up_angle = int(up_angle)
		except Exception, e:
			tb = unicode(traceback.format_exc()).encode("utf-8").encode('string_escape')
			client.wfile.write(b"Fail: " + tb + b"\n")
			return
		with self.lock:
			client.request_gesture(self, what, up_angle)
			client.wfile.write(b"OK.\n")
	elif message.startswith("Restart."):
		self.on_sa_restart()
	elif message.startswith("Gestured:"):
		gstr = message[9:].strip()
		client.gesture_action.gesture(client.mapper, gstr)
		with self.lock:
			client.wfile.write(b"OK.\n")
	elif message.startswith("Selected:"):
		menuaction = None
		def press(mapper):
			try:
				menuaction.button_press(mapper)
				client.mapper.schedule(0.1, release)
			except Exception, e:
				log.error("Error while processing menu action")
				log.exception(e)
		def release(mapper):
			try:
				menuaction.button_release(mapper)
			except Exception, e:
				log.error("Error while processing menu action")
				log.exception(e)
		
		with self.lock:
			try:
				menu_id, item_id = shsplit(message)[1:]
				menuaction = None
				if menu_id in (None, "None"):
					menuaction = self.osd_ids[item_id]
				elif "." in menu_id:
					# TODO: Move this common place
					data = json.loads(open(menu_id, "r").read())
					menudata = MenuData.from_json_data(data, TalkingActionParser())
					menuaction = menudata.get_by_id(item_id).action
				else:
					menuaction = client.mapper.profile.menus[menu_id].get_by_id(item_id).action
				client.wfile.write(b"OK.\n")
			except:
				log.warning("Selected menu item is no longer valid.")
				client.wfile.write(b"Fail: Selected menu item is no longer valid\n")
			if menuaction:
				client.mapper.schedule(0, press)
	elif message.startswith("Register:"):
		with self.lock:
			if message.strip().endswith("osd"):
				if self.osd_daemon: self.osd_daemon.close()
				self.osd_daemon = client
				log.info("Registered scc-osd-daemon")
			elif message.strip().endswith("autoswitch"):
				if self.autoswitch_daemon: self.autoswitch_daemon.close()
				self.autoswitch_daemon = client
				log.info("Registered scc-autoswitch-daemon")
			client.wfile.write(b"OK.\n")
	else:
		client.wfile.write(b"Fail: Unknown command\n")
	*/
	
	LOG("Unknown command: %s", command);
	send_error(client, tokens, "Fail: Unknown command\n");
	return;
}

static inline void send_tag(Client* client) {
	if (client->tag != NULL) {
		sccd_socket_send(client, client->tag);
		sccd_socket_send(client, " ");
		free(client->tag);
		client->tag = NULL;
	}
}

static inline void send_ok(Client* client, Tokens* tokens) {
	tokens_free(tokens);
	send_tag(client);
	sccd_socket_send(client, "OK.\n");
}

static inline void send_error(Client* client, Tokens* tokens, const char* error) {
	tokens_free(tokens);
	send_tag(client);
	sccd_socket_send(client, error);
}

static inline void send_error_dealoc(Client* client, Tokens* tokens, char* error) {
	tokens_free(tokens);
	if (error != NULL) {
		send_tag(client);
		sccd_socket_send(client, error);
		free(error);
	} else {
		sccd_drop_client_asap(client);
	}
}
