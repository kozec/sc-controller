#pragma once
#include <gtk/gtk.h>

// typedef struct {
// 	GtkWidget* (*generate_widget)(void* menu_item);
// } MenuCallbacks;

typedef struct SCCClient SCCClient;
typedef struct StickController StickController;
typedef void (*StickControllerCallback)(int dx, int dy, void* userdata);

/**
 * Installs CSS provider if it is not already installed.
 * This takes care of OSD colors and entire look-and-feel.
 */
void install_css_provider();
/**
 * (Re)installs CSS provider even if it was already installed.
 * Called after CSS color config is changed.
 */
void reconfigure_css_provider();

typedef struct _OSDMenu OSDMenu;
typedef struct OSDMenuSettings OSDMenuSettings;
/** Parses OSD menu command line arguments */
bool osd_menu_parse_args(int argc, char** argv, const char** usage, OSDMenuSettings* settings);
/**
 * Configures menu to use already connected client.
 * 'slave_mapper' may be NULL in which case new is created.
 *
 * Returns false if 'slave_mapper' is NULL and cannot be allocated.
 */
bool osd_menu_set_client(OSDMenu* mnu, SCCClient* client, Mapper* slave_mapper);
/**
 * Asks daemon to lock required inputs. This should be used only after 'osd_menu_set_client"
 * 'ready' or 'exit' signal is emitted to signal success or failure.
 */
void osd_menu_lock_inputs(OSDMenu* mnu);
/** Called to supply input events send from daemon */
void osd_menu_parse_event(OSDMenu* mnu, SCCClient* c, uint32_t handle,
						SCButton button, PadStickTrigger pst, int values[]);

#define STICK_CONTROLLER_REPEAT_DELAY 200 /* ms */
/** Creates new StickController. Returns NULL on failure. */
StickController* stick_controller_create(StickControllerCallback cb, void* userdata);
/** Should be called from client's event callback */
void stick_controller_feed(StickController* sc, int values[]);
/** Frees StickController data */
void stick_controller_free(StickController* sc);
/** Converts KEY_* constant to GDK constant */
guint keycode_to_gdk_hw_keycode(int64_t key);

