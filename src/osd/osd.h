#pragma once
#include <gtk/gtk.h>

// typedef struct {
// 	GtkWidget* (*generate_widget)(void* menu_item);
// } MenuCallbacks;

typedef struct StickController StickController;
typedef void (*StickControllerCallback)(int dx, int dy, void* userdata);

void install_css_provider();

#define STICK_CONTROLLER_REPEAT_DELAY 200 /* ms */
/** Creates new StickController. Returns NULL on failure. */
StickController* stick_controller_create(StickControllerCallback cb, void* userdata);
/** Should be called from client's event callback */
void stick_controller_feed(StickController* sc, int values[]);
/** Frees StickController data */
void stick_controller_free(StickController* sc);
