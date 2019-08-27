#pragma once
#include "scc/utils/intmap.h"
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

extern const char* KW_OSK_CURSOR;
extern const char* KW_OSK_CLOSE;
extern const char* KW_OSK_PRESS;

#define MAX_HELP_AREAS		2
#define MAX_HELP_LINE_LEN	256

struct Limits {
	double						x0, y0, x1, y1;
};

struct HelpArea {
	bool						align_right;
	struct Limits				limits;
};

typedef struct {
	SCButton					scbutton;
	bool						align_right;
	char						text[MAX_HELP_LINE_LEN];
} HelpLine;

typedef LIST_TYPE(HelpLine) HelpLineList;

typedef struct _OSDKeyboardPrivate {
	SCCClient*					client;
	GSource*					client_src;
	Mapper*						slave_mapper;
	ButtonList					buttons;
	GtkWidget*					draw_area;
	const char*					controller_id;
	GdkKeymap*					keymap;
	dvec_t						size;
	struct {
		dvec_t					position;
		int						pressed_button_index;
		GdkPixbuf*				image;
	}							cursors[2];
	intmap_t					button_images;
	struct Limits				limits[3];
	struct HelpArea				help_areas[MAX_HELP_AREAS];
	HelpLineList				help_lines;
	uint8_t						cursor_count;
	GdkRGBA						color_pressed;
	GdkRGBA						color_hilight;
	GdkRGBA						color_button2;
	GdkRGBA						color_button1;
	GdkRGBA						color_button1_border;
	GdkRGBA						color_text;
} OSDKeyboardPrivate;


struct Button {
	Action*						action;
	Keycode						keycode;	// Used when aciton bound on key represents virtual key
	const char*					label;		// Used with other actions
	SCButton					scbutton;
	int							index;
	bool						dark;
	dvec_t						pos;
	dvec_t						size;
};

void register_keyboard_actions();
bool load_keyboard_data(const char* filename, OSDKeyboardPrivate* priv);
bool is_button_under_cursor(OSDKeyboardPrivate* priv, int index, struct Button* b);
void load_colors(OSDKeyboardPrivate* priv);
bool init_display(OSDKeyboard* kbd, OSDKeyboardPrivate* priv);
void generate_help_lines(OSDKeyboardPrivate* priv);
bool on_redraw(GtkWidget* draw_area, cairo_t* ctx, void* priv);

