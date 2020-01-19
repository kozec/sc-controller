/**
 * SC-Controller - Radial OSD Menu
 *
 * Menu in circle.
 */
#define LOG_TAG "OSD"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/osd/osd_window.h"
#include "scc/osd/menu_icon.h"
#include "scc/osd/osd_menu.h"
#include "scc/menu_data.h"
#include "scc/config.h"
#include "scc/tools.h"
#include <gtk/gtk.h>
#include <math.h>
#ifdef _WIN32
	#include <windows.h>
	#include <gdk/gdkwin32.h>
#else
	#include <X11/extensions/Xfixes.h>
	#include <X11/extensions/shape.h>
	#include <X11/Xutil.h>
	#include <gdk/gdkx.h>
#endif

#define BORDER_WIDTH		2
#define LINE_WIDTH			1.5
#define FONT_SIZE			24
#define HELP_FONT_SIZE		16
#define MAX_ORBITS			5
#define BOX_PADDING_X		5
#define BOX_PADDING_Y		10

struct RadialMenuData {
	GdkRGBA		color_background;
	GdkRGBA		color_border;
	GdkRGBA		color_text;
	GdkRGBA		color_menuitem_border;
	GdkRGBA		color_menuitem_hilight;
	GdkRGBA		color_menuitem_hilight_text;
	GdkRGBA		color_menuitem_hilight_border;
	GdkRGBA		color_menuseparator;
};

struct Position {
	size_t		index;
	uint32_t	orbit;
	uint32_t	orbit_index;
	double		icon_size;
	double		icon_y;
	double		a0;
	double		a1;
	double		y0;
	double		y1;
};


static void ff(void* a) {
	// TODO: Remove this once its actually called
	LOG("ff %p", a);
	free(a);
}


static inline void draw_pie_piece(cairo_t* ctx, bool is_selected,
				struct RadialMenuData* plugin_data, MenuItem* i,
				double r, double cx, double cy) {
	double x, y;
	cairo_path_t* p;
	struct Position* pos = g_object_get_data(G_OBJECT(i->userdata), "scc-menu-poistion");
	GdkPixbuf* pb = menu_icon_get_pixbuf(i->userdata);
	GdkRGBA* background_color;
	GdkRGBA* border_color;
	GdkRGBA* text_color;
	if (is_selected) {
		background_color = &plugin_data->color_menuitem_hilight;
		border_color = &plugin_data->color_menuitem_hilight_border;
		text_color = &plugin_data->color_menuitem_hilight_text;
	} else {
		background_color = &plugin_data->color_background;
		border_color = &plugin_data->color_menuitem_border;
		text_color = &plugin_data->color_text;
	}
	
	if (pos->a0 != pos->a1) {
		cairo_arc(ctx, cx, cy, pos->y0 * r, pos->a0, pos->a0);
		cairo_get_current_point(ctx, &x, &y);
		cairo_new_path(ctx);
		cairo_move_to(ctx, x, y);
		cairo_arc(ctx, cx, cy, pos->y0 * r, pos->a0, pos->a0);
		cairo_arc(ctx, cx, cy, pos->y1 * r, pos->a0, pos->a1);
		cairo_arc_negative(ctx, cx, cy, pos->y0 * r, pos->a1, pos->a0);
		p = cairo_copy_path(ctx);
		gdk_cairo_set_source_rgba(ctx, background_color);
		cairo_fill(ctx);
		cairo_append_path(ctx, p);
		cairo_path_destroy(p);
		gdk_cairo_set_source_rgba(ctx, border_color);
		cairo_stroke(ctx);
		
		cairo_move_to(ctx, x, y);
		cairo_arc(ctx, cx, cy,
			r * pos->icon_y,
			// (pos->y0 + (pos->y1 - pos->y0) * 0.5),
			pos->a0 + (pos->a1 - pos->a0) * 0.5,
			pos->a0 + (pos->a1 - pos->a0) * 0.5);
		cairo_get_current_point(ctx, &x, &y);
		cairo_new_path(ctx);
		cairo_save(ctx);
		cairo_translate(ctx, x - pos->icon_size * 0.5, y - pos->icon_size * 0.5);
		menu_icon_draw_pixbuf(pb, ctx, pos->icon_size, pos->icon_size, text_color);
		cairo_restore(ctx);
	} else {
		cairo_arc(ctx, cx, cy, pos->y1 * r, 0, 2.0 * M_PI);
		gdk_cairo_set_source_rgba(ctx, border_color);
		p = cairo_copy_path(ctx);
		gdk_cairo_set_source_rgba(ctx, background_color);
		cairo_fill(ctx);
		cairo_append_path(ctx, p);
		cairo_path_destroy(p);
		gdk_cairo_set_source_rgba(ctx, border_color);
		cairo_stroke(ctx);
		
		cairo_save(ctx);
		cairo_translate(ctx, cx - pos->icon_size * 0.5, cy - pos->icon_size * 0.5);
		menu_icon_draw_pixbuf(pb, ctx, pos->icon_size, pos->icon_size, text_color);
		cairo_restore(ctx);
	}
	
	if (is_selected && (i->name != NULL)) {
		cairo_text_extents_t extents;
		StrBuilder* sb = strbuilder_new();
		if ((sb == NULL) || (!strbuilder_add(sb, i->name))) {
			strbuilder_free(sb);
			return;
		}
		cairo_text_extents(ctx, strbuilder_get_value(sb), &extents);
		// Draw box
		double a = pos->a0 + 0.5 * (pos->a1 - pos->a0);
		double y = ((a > M_PI) || (a < 0)) ? cy * 1.6 : cy * 0.48;
		double box_width = cx * 2.0 * 0.65;
		cairo_save(ctx);
		cairo_move_to(ctx,
				cx - box_width * 0.5 - BOX_PADDING_X,
				y + extents.y_bearing - BOX_PADDING_Y
		);
		cairo_rel_line_to(ctx, box_width + 2.0 * BOX_PADDING_X, 0);
		cairo_rel_line_to(ctx, 0, -extents.y_bearing + 2.0 * BOX_PADDING_Y);
		cairo_rel_line_to(ctx, -box_width - 2.0 * BOX_PADDING_X, 0);
		cairo_rel_line_to(ctx, 0, extents.y_bearing - 2.0 * BOX_PADDING_Y);
		p = cairo_copy_path(ctx);
		gdk_cairo_set_source_rgba(ctx, &plugin_data->color_background);
		cairo_fill(ctx);
		cairo_append_path(ctx, p);
		// Cut text so it fits the box
		bool threedots_added = false;
		while ((strbuilder_len(sb) > 4) && (extents.width > box_width - 2.0 * BOX_PADDING_X)) {
			if (threedots_added) {
				strbuilder_rtrim(sb, 4);
				if (!strbuilder_add(sb, "..."))
					break;
			} else {
				strbuilder_rtrim(sb, 1);
				if (!strbuilder_add(sb, "..."))
					break;
				threedots_added = true;
			}
			cairo_text_extents(ctx, strbuilder_get_value(sb), &extents);
		}
		// Draw text
		gdk_cairo_set_source_rgba(ctx, &plugin_data->color_text);
		cairo_stroke(ctx);
		cairo_move_to(ctx, cx - extents.width * 0.5, y);
		cairo_show_text(ctx, strbuilder_get_value(sb));
		cairo_stroke(ctx);
		cairo_restore(ctx);
		strbuilder_free(sb);
	}
}

static bool on_redraw(GtkWidget* a, cairo_t* ctx, void* _mnu) {
	OSDMenu* mnu = (OSDMenu*)_mnu;
	struct RadialMenuData* plugin_data = osd_menu_get_plugin_data(mnu);
	int width = gtk_widget_get_allocated_width(a);
	int height = gtk_widget_get_allocated_height(a);
	// TODO: Fonts?
#ifndef _WIN32
	cairo_select_font_face(ctx, "DejaVu Sans", 0, 0); // CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
#else
	cairo_select_font_face(ctx, "Verdana Normal", 0, 0); // CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
#endif
	cairo_set_font_size(ctx, FONT_SIZE);
	
	// Compute stuff
	double cx = (double)width * 0.5;
	double cy = (double)height * 0.5;
	double r = min(cx, cy) - (double)BORDER_WIDTH;
	
	// Draw background
	cairo_move_to(ctx, cx + r, cy);
	cairo_arc(ctx, cx, cy, r, 0, 2.0 * M_PI);
	// Outline is drawn little thicker
	// to cover difference between X's and Cairo's idea of circle
#ifndef _WIN32
	cairo_set_line_width(ctx, BORDER_WIDTH * 1.5);
#else
	// It's even worse on Windows
	cairo_set_line_width(ctx, BORDER_WIDTH * 10.0);
#endif
	
	cairo_path_t* outline = cairo_copy_path(ctx);
	gdk_cairo_set_source_rgba(ctx, &plugin_data->color_background);
	cairo_fill(ctx);
	
	// Draw items
	MenuItem* selected = osd_menu_get_selected(mnu);
	MenuData* data = osd_menu_get_menu_data(mnu);
	cairo_set_line_width(ctx, LINE_WIDTH);
	ListIterator it = iter_get(data);
	FOREACH(MenuItem*, i, it) {
		if ((i->userdata != NULL) && (i != selected))
			draw_pie_piece(ctx, false, plugin_data, i, r, cx, cy);
	}
	if ((selected != NULL) && (selected->userdata != NULL))
			draw_pie_piece(ctx, true, plugin_data, selected, r, cx, cy);
	iter_free(it);
	
	// Draw outline
	// Outline is drawn little thicker
	// to cover difference between X's and Cairo's idea of circle
	cairo_set_line_width(ctx, BORDER_WIDTH * 1.5);
	cairo_append_path(ctx, outline);
	cairo_path_destroy(outline);
	gdk_cairo_set_source_rgba(ctx, &plugin_data->color_border);
	cairo_stroke(ctx);
	
	return false;
}


void load_colors(struct RadialMenuData* data) {
	Config* config = config_load();
	ASSERT(config);
	
	gdk_rgba_parse(&data->color_background, config_get(config, "osd_colors/background"));
	gdk_rgba_parse(&data->color_border, config_get(config, "osd_colors/border"));
	gdk_rgba_parse(&data->color_text, config_get(config, "osd_colors/text"));
	gdk_rgba_parse(&data->color_menuitem_border, config_get(config, "osd_colors/menuitem_border"));
	gdk_rgba_parse(&data->color_menuitem_hilight, config_get(config, "osd_colors/menuitem_hilight"));
	gdk_rgba_parse(&data->color_menuitem_hilight_text, config_get(config, "osd_colors/menuitem_hilight_text"));
	gdk_rgba_parse(&data->color_menuitem_hilight_border, config_get(config, "osd_colors/menuitem_hilight_border"));
	gdk_rgba_parse(&data->color_menuseparator, config_get(config, "osd_colors/menuseparator"));
	
	RC_REL(config);
}

static GtkWidget* make_icon(MenuItem* i, float size, uint32_t* orbit, uint32_t* items_per_orbit) {
	GtkWidget* w;
	char* filename;
	bool has_colors;
	switch (i->type) {
	case MI_DUMMY:
		return NULL;
	case MI_ACTION:
	case MI_SUBMENU:
		w = NULL;
		filename = scc_find_icon(i->icon, false, &has_colors, NULL, NULL);
		if (filename != NULL) {
			w = GTK_WIDGET(menu_icon_new(filename, has_colors));
			free(filename);
		}
		if (w == NULL) {
			filename = scc_find_icon("system/unknown", false, &has_colors, NULL, NULL);
			w = GTK_WIDGET(menu_icon_new(filename, has_colors));
			free(filename);
		}
		if (w != NULL)
			gtk_widget_set_name(GTK_WIDGET(w), "icon");
		break;
		return NULL;
		/*
		w = make_menu_row(i->icon, size);
		gtk_widget_set_name(GTK_WIDGET(w), "osd-menu-item");
		break;
		*/
	case MI_SEPARATOR: {
		if (items_per_orbit[*orbit] > 0) {
			*orbit = *orbit + 1;
			// LOG("Separator, moving to orbit %i", *orbit);
		}
		return NULL;
					   }
	default:
		return NULL;
	}
	if (w != NULL) {
		struct Position* pos = malloc(sizeof(struct Position));
		ASSERT(pos != NULL);
		items_per_orbit[*orbit] ++;
		pos->orbit = *orbit;
		pos->icon_size = 100;
		pos->a0 = pos->y0 = 0;
		pos->a1 = pos->y1 = 1;
		g_object_set_data(G_OBJECT(w), "scc-menu-item-data", i);
		g_object_set_data_full(G_OBJECT(w), "scc-menu-poistion", pos, ff);
	}
	return w;
}

static bool on_size_allocate(GtkWidget* w, GdkRectangle* alloc, void* _mnu) {
	if (!gtk_widget_get_realized(w))
		return false;
	MenuData* data = osd_menu_get_menu_data((OSDMenu*)_mnu);
	int width = alloc->width;
	int height = alloc->height;
	int r = min(width, height) - BORDER_WIDTH * 0.5;
	
	// Turns _parent window_ of menu into nice, round circle
#ifndef _WIN32
	Display* dpy = gdk_x11_get_default_xdisplay();
	ASSERT(dpy != NULL);
	GdkWindow* gdk_window = gtk_widget_get_window(w);
	ASSERT(gdk_window != NULL);
	XID win = GDK_WINDOW_XID(gdk_window);
	Pixmap pixmap = XCreatePixmap(dpy, win, width, height, 1);
	GC gc = XCreateGC(dpy, pixmap, 0, NULL);
	XSetForeground(dpy, gc, 0);
	XFillRectangle(dpy, pixmap, gc, 0, 0, width, height);
	XSetForeground(dpy, gc, 1);
	XSetBackground(dpy, gc, 1);
	XFillArc(dpy, pixmap, gc, 0, 0, r, r, 0, 360*64);
	XFlushGC(dpy, gc);
	XFlush(dpy);
	
	XShapeCombineMask(dpy, win, ShapeBounding, 0, 0, pixmap, ShapeSet);
	XFlush(dpy);
	
	XFreeGC(dpy, gc);
	XFreePixmap(dpy, pixmap);
	XFlush(dpy);
#else
	// TODO: Windows? How?
	GdkWindow* gdk_window = gtk_widget_get_window(GTK_WIDGET(_mnu));
	HWND hwnd = gdk_win32_window_get_handle(gdk_window);
	HRGN region = CreateRoundRectRgn(0, 0, width, height, width, height);
	SetWindowRgn(hwnd, region, true);
#endif
	
	// Computes position of every icon and pie piece on the canvas
	ListIterator it = iter_get(data);
	uint32_t orbits = 0;
	uint32_t items_per_orbit[MAX_ORBITS];
	for (uint32_t i=0; i<MAX_ORBITS; i++)
		items_per_orbit[i] = 0;
	FOREACH(MenuItem*, i, it) {
		if (i->userdata != NULL) {
			struct Position* pos = g_object_get_data(G_OBJECT(i->userdata), "scc-menu-poistion");
			pos->orbit_index = items_per_orbit[pos->orbit] ++;
			orbits = max(orbits, pos->orbit + 1);
		}
	}
	for (uint32_t i=1; i<MAX_ORBITS; i++)
		if (items_per_orbit[i] == 1)
			items_per_orbit[i] = 2;
	
	bool has_center = (orbits > 1) && (items_per_orbit[0] == 1);
	// LOG("Orbits: %i (center %i)", orbits, has_center);
	iter_reset(it);
	FOREACH(MenuItem*, i, it) {
		if (i->userdata != NULL) {
			struct Position* pos = g_object_get_data(G_OBJECT(i->userdata), "scc-menu-poistion");
			// items_per_orbit[pos->orbit] = max(2, items_per_orbit[pos->orbit]);
			double start = M_PI * (-0.5 - 1.0 / (double)(items_per_orbit[pos->orbit]));
			if (orbits <= 1) {
				// If there is only one orbit, it starts from 1/4 of radius
				pos->y0 = 0.25;
				pos->y1 = 1.00;
			} else if (has_center && (pos->orbit == 0)) {
				// Special case, multiple orbits with single item in center
				pos->y0 = 0;
				pos->y1 = 0.02 + 0.98 * (pos->orbit+1) / (double)orbits;
			} else if (has_center) {
				pos->y0 = 0.02 + 0.98 * (pos->orbit) / (double)orbits;
				pos->y1 = 0.02 + 0.98 * (pos->orbit+1) / (double)orbits;
			} else {
				// If there are multiple orbits, 1st is reserved for "center"
				// and rest is split from 1/5 of radius to corner
				pos->y0 = 0.2 + 0.8 * (pos->orbit) / (double)orbits;
				pos->y1 = 0.2 + 0.8 * (pos->orbit+1) / (double)orbits;
			}
			if (items_per_orbit[pos->orbit] > 1) {
				pos->a0 = start + (pos->orbit_index+0) * 2.0 * M_PI / (double)(items_per_orbit[pos->orbit]);
				pos->a1 = start + (pos->orbit_index+1) * 2.0 * M_PI / (double)(items_per_orbit[pos->orbit]);
				if (orbits > 1) {
					pos->icon_y = (pos->y0 + (pos->y1 - pos->y0) * 0.5);
					pos->icon_size = 0.5 * (double)r * min(
						0.8 * (pos->y1 - pos->y0),
						sqrt(tan((pos->a1 - pos->a0) * 0.5)) * (pos->y1 - pos->y0)
					);
				} else {
					pos->icon_y = (pos->y0 + (pos->y1 - pos->y0) * 0.6);
					pos->icon_size = 0.5 * (double)r
						* sqrt(tan((pos->a1 - pos->a0) * 0.3))
						* (pos->y1 - pos->y0);
				}
			} else {
				pos->icon_y = (pos->y0 + (pos->y1 - pos->y0) * 0.5),
				pos->icon_size = r * 0.2;
				pos->a0 = 0;
				pos->a1 = 0; // 2.0 * M_PI;
			}
			// LOG("Item %p a=<%g,%g> y=<%g,%g>",
			// 		i, pos->a0 * 180.0 / M_PI, pos->a1 * 180.0 / M_PI,
			// 		pos->y0, pos->y1);
		}
	}
	iter_free(it);
	return false;
}


DLL_EXPORT GtkWidget* osd_menu_create_widgets(OSDMenu* mnu, OSDMenuSettings* settings) {
	struct RadialMenuData* plugin_data = malloc(sizeof(struct RadialMenuData));
	ASSERT(plugin_data != NULL);
	load_colors(plugin_data);
	osd_menu_set_plugin_data(mnu, plugin_data);
	
	MenuData* data = osd_menu_get_menu_data(mnu);
	GtkWidget* a = gtk_drawing_area_new();
	gtk_widget_set_size_request(a, 400, 400);
	g_signal_connect(G_OBJECT(a), "draw", (GCallback)&on_redraw, mnu);
	g_signal_connect(G_OBJECT(mnu), "size-allocate", (GCallback)&on_size_allocate, mnu);
	
	uint32_t orbit = 0;
	uint32_t items_per_orbit[MAX_ORBITS];
	for (uint32_t i=0; i<MAX_ORBITS; i++)
		items_per_orbit[i] = 0;
	ListIterator it = iter_get(data);
	FOREACH(MenuItem*, i, it)
		i->userdata = make_icon(i, settings->icon_size, &orbit, items_per_orbit);
	iter_free(it);
	return a;
}

DLL_EXPORT void osd_menu_handle_input(OSDMenu* mnu, SCButton button, PadStickTrigger pst, OSDMenuInput translated_input, int _values[]) {
	double a, y;
	ListIterator it;
	MenuData* data = osd_menu_get_menu_data(mnu);
	union {
		int* values;
		int pressed;
		struct { int x; int y; };
	}* values = (void*)_values;
	
	switch (translated_input) {
	case OMI_CONFIRM:
		if (!values->pressed)
			osd_menu_confirm(mnu);
		break;
	case OMI_CANCEL:
		// if (values->pressed)
		osd_window_exit(OSD_WINDOW(mnu), -1);
		break;
	case OMI_CONTROL:
		a = atan2((double)values->x, (double)values->y) - 0.5 * M_PI;
		y = sqrt(POW2((double)values->x) + POW2((double)values->y)) / (double)STICK_PAD_MAX;
		it = iter_get(data);
		FOREACH(MenuItem*, i, it) {
			if (i->userdata != NULL) {
				struct Position* pos = g_object_get_data(G_OBJECT(i->userdata), "scc-menu-poistion");
				bool in_pie = (
					((a >= pos->a0) && (a <= pos->a1))
					|| ((a + 2.0 * M_PI >= pos->a0) && (a + 2.0 * M_PI <= pos->a1))
					|| (pos->a0 == pos->a1)
				);
				if (in_pie && (y >= pos->y0) && (y <= pos->y1)) {
					// LOG("GOT ITEM %p @%g (in <%g,%g>)", i,
					// 	a * 180.0 / M_PI,
					// 	pos->a0 * 180.0 / M_PI,
					// 	pos->a1 * 180.0 / M_PI
					// );
					osd_menu_select(mnu, i);
					gtk_widget_queue_draw(GTK_WIDGET(mnu));
					break;
				}
			}
		}
		iter_free(it);
		// LOG(">>> INPUT %i %i %g", values->x, values->y, a);
		break;
	case OMI_NOT_TRANSLATED:
		break;
	}
}

DLL_EXPORT void osd_menu_free_plugin_data(OSDMenu* mnu, void* plugin_data) {
	MenuData* data = osd_menu_get_menu_data(mnu);
	free(plugin_data);
	ListIterator it = iter_get(data);
	FOREACH(MenuItem*, i, it) {
		if (i->userdata != NULL) {
			// TODO: Not even this deallocates "scc-menu-poistion"
			// TODO: Is it because process is exiting? Test with osd-daemon
			gtk_widget_destroy(GTK_WIDGET(i->userdata));
		}
	}
	iter_free(it);
}

