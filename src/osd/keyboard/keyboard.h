#pragma once
#include "scc/utils/list.h"
#include "scc/utils/math.h"
#include "scc/parser.h"
#include <glib.h> // glib.h has to be included before client.h
#include <gdk-pixbuf/gdk-pixbuf.h>
#include <gtk/gtk.h>
#include "scc/client.h"

typedef struct _OSDKeyboard	OSDKeyboard;
typedef struct Button Button;
typedef LIST_TYPE(Button) ButtonList;

struct Limits {
	double				x0, y0, x1, y1;
};

typedef struct _OSDKeyboardPrivate {
	SCCClient*			client;
	Mapper*				slave_mapper;
	ButtonList			buttons;
	GtkWidget*			draw_area;
	const char*			controller_id;
	GdkKeymap*			keymap;
	dvec_t				size;
	dvec_t				cursors[2];
	GdkPixbuf*			cursor_images[2];
	struct Limits		limits[3];
	uint8_t				cursor_count;
	GdkRGBA				color_pressed;
	GdkRGBA				color_hilight;
	GdkRGBA				color_button2;
	GdkRGBA				color_button1;
	GdkRGBA				color_button1_border;
	GdkRGBA				color_text;
} OSDKeyboardPrivate;


struct Button {
	Action*				action;
	Keycode				keycode;	// Used when aciton bound on key represents virtual key
	const char*			label;		// Used with other actions
	bool				dark;
	bool				pressed;
	bool				hilighted;
	dvec_t				pos;
	dvec_t				size;
};

bool load_keyboard_data(const char* filename, OSDKeyboardPrivate* priv);
void load_colors(OSDKeyboardPrivate* priv);
bool init_display(OSDKeyboard* kbd, OSDKeyboardPrivate* priv);
bool on_redraw(GtkWidget* draw_area, cairo_t* ctx, void* priv);

