#define LOG_TAG "OSD"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
#include "scc/osd/menu_icon.h"
#include "scc/conversions.h"
#include "scc/controller.h"
#include "scc/config.h"
#include "scc/tools.h"
#include "../osd.h"
#include "keyboard.h"
#ifdef _WIN32
	#include <windows.h>
#else
	#include <X11/Xutil.h>
	#include <X11/extensions/XKB.h>
	#include <X11/XKBlib.h>
	#include <gdk/gdkx.h>
#endif

#define LINE_WIDTH			2
#define FONT_SIZE			38
#define HELP_FONT_SIZE		16

inline static void button_as_path(cairo_t* ctx, Button* b) {
	cairo_move_to(ctx, b->pos.x, b->pos.y);
	cairo_rel_line_to(ctx, b->size.x, 0);
	cairo_rel_line_to(ctx, 0, b->size.y);
	cairo_rel_line_to(ctx, -b->size.x, 0);
	cairo_rel_line_to(ctx, 0, -b->size.y);
}

static GdkPixbuf* get_button_pixbuf(OSDKeyboardPrivate* priv, SCButton button, int size) {
	GdkPixbuf* pbuf = NULL;
	GError* err = NULL;
	if (intmap_get(priv->button_images, button, (any_t)&pbuf) == MAP_OK) {
		// Already cached
		return pbuf;
	}
	char* path = scc_find_button_image(button, false, NULL);
	if (path != NULL) {
		// TODO: Deallocate these
		pbuf = gdk_pixbuf_new_from_file_at_size(path, size, size, &err);
		free(path);
		if (err != NULL) {
			LERROR("Failed to load button image: %s", err->message);
			pbuf = NULL;
		}
	}
	intmap_put(priv->button_images, button, pbuf);
	return pbuf;
}

bool on_redraw(GtkWidget* draw_area, cairo_t* ctx, void* _priv) {
	OSDKeyboardPrivate* priv = (OSDKeyboardPrivate*)_priv;
	StrBuilder* label = strbuilder_new();
	cairo_font_extents_t fextents;
	cairo_font_extents_t hextents;
	ASSERT(priv->draw_area == draw_area);
#ifndef _WIN32
	XkbStateRec xkb_state;
	Display* dpy = gdk_x11_get_default_xdisplay();
	XkbGetState(dpy, XkbUseCoreKbd, &xkb_state);
#endif
	
	// TODO: It would be cool to use user-set font here, but cairo doesn't
	// have glyph replacement and most of default fonts (Ubuntu, Cantarell,
	// similar shit) misses pretty-much everything but letters, notably ↲
	//
	// For that reason, DejaVu Sans is hardcoded for now. On systems
	// where DejaVu Sans is not available, Cairo will automatically fallback
	// to default font.
#ifndef _WIN32
	cairo_select_font_face(ctx, "DejaVu Sans", 0, 0); // CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
#else
	cairo_select_font_face(ctx, "Verdana Normal", 0, 0); // CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
	// Arial Normal
	// Arial Bold
	// Tahoma Normal
	// Verdana Normal
#endif
	cairo_set_line_width(ctx, LINE_WIDTH);
	cairo_set_font_size(ctx, HELP_FONT_SIZE);
	cairo_font_extents(ctx, &hextents);
	cairo_set_font_size(ctx, FONT_SIZE);
	cairo_font_extents(ctx, &fextents);
	int scbutton_size = hextents.height;
	
	// Buttons
	FOREACH_IN(Button*, b, priv->buttons) {
		bool hilighted = false;
		bool pressed = false;
		for (int index=0; index<2; index++) {
			pressed = pressed || (priv->cursors[index].pressed_button_index == b->index);
			hilighted = hilighted || (is_button_under_cursor(priv, index, b));
		}
		if (pressed)
			gdk_cairo_set_source_rgba(ctx, &priv->color_pressed);
		else if (hilighted)
			gdk_cairo_set_source_rgba(ctx, &priv->color_hilight);
		else if (b->dark)
			gdk_cairo_set_source_rgba(ctx, &priv->color_button2);
		else
			gdk_cairo_set_source_rgba(ctx, &priv->color_button1);
		
		// filled rectangle
		button_as_path(ctx, b);
		cairo_fill(ctx);
		
		// border
		gdk_cairo_set_source_rgba(ctx, &priv->color_button1_border);
		button_as_path(ctx, b);
		cairo_stroke(ctx);
		
		// help icon
		if (b->scbutton) {
			GdkPixbuf* pbuf = get_button_pixbuf(priv, b->scbutton, scbutton_size);
			if (pbuf != NULL) {
				int height = gdk_pixbuf_get_height(pbuf);
				cairo_save(ctx);
				cairo_translate(ctx,
					(int)(b->pos.x + b->size.x - scbutton_size - 2),
					(int)(b->pos.y + b->size.y - height - 2)
				);
				menu_icon_draw_pixbuf(pbuf, ctx, 0, 0, &priv->color_text);
				cairo_restore(ctx);
			}
		}
		
		// label
		if ((b->keycode) || (b->label)) {
			strbuilder_clear(label);
			if (b->keycode) {
#ifndef _WIN32
				// LOG(" >> current group: %i", xkb_state.group);
				guint mt = gdk_keymap_get_modifier_state(priv->keymap);
				GdkModifierType consumed_modifiers;
				guint keyval;
				bool translated = gdk_keymap_translate_keyboard_state(
							priv->keymap, scc_keycode_to_x11(b->keycode),
							mt, xkb_state.group, &keyval, NULL, NULL,
							&consumed_modifiers);
				guint32 unicode = gdk_keyval_to_unicode(keyval);
				// TODO: Maybe use images
				if (unicode == 8)
					strbuilder_addf(label, "←");
				else if (unicode == 9)
					strbuilder_addf(label, "⇥");
				else if (unicode == 13)
					strbuilder_addf(label, "↲");
				else if (unicode == 27)
					strbuilder_addf(label, "esc");
				else if (unicode == 32)
					strbuilder_addf(label, " ");
				else if (!translated && (b->keycode == 41))
					// TODO: Find why is grave/tilde not getting translated
					strbuilder_addf(label, "~");
				else if (translated && (unicode > 32)) // 32 = space
					strbuilder_addf(label, "%lc", unicode);
#else
				char* str = scc_action_get_description(b->action, AC_OSD);
				strbuilder_addf(label, "%s", str);
				free(str);
#endif
			}
			if (strbuilder_len(label) == 0) {
				if (b->label != NULL)
					strbuilder_add(label, (char*)b->label);
			}
			cairo_text_extents_t extents;
			cairo_save(ctx);
			gdk_cairo_set_source_rgba(ctx, &priv->color_text);
			cairo_text_extents(ctx, strbuilder_get_value(label), &extents);
			button_as_path(ctx, b);
			cairo_clip(ctx);
			cairo_move_to(ctx,
				b->pos.x + (b->size.x * 0.5) - (extents.width * 0.5) - extents.x_bearing,
				b->pos.y + (b->size.y * 0.5) + (fextents.height * 0.25)
			);
			cairo_show_text(ctx, strbuilder_get_value(label));
			cairo_stroke(ctx);
			cairo_restore(ctx);
		}
	}
	strbuilder_free(label);
	
	for (int i=0; i<=1; i++) {
		cairo_save(ctx);
		cairo_translate(ctx, priv->cursors[i].position.x, priv->cursors[i].position.y);
		gdk_cairo_set_source_pixbuf(ctx, priv->cursors[i].image, 0, 0);
		cairo_paint(ctx);
		cairo_restore(ctx);
	}
	
	// TODO: Overlay? Is it really needed?
	// Gdk.cairo_set_source_pixbuf(ctx, self.overlay.get_pixbuf(), 0, 0)
	// ctx.paint()
	
	// Help
	gdk_cairo_set_source_rgba(ctx, &priv->color_text);
	cairo_set_font_size(ctx, HELP_FONT_SIZE);
	
	for (int align_right=0; align_right<=1; align_right++) {
		int area_index = -1;
		for (int i=0; i<MAX_HELP_AREAS; i++) {
			if (priv->help_areas[i].align_right == align_right) {
				area_index = i;
				break;
			}
		}
		if (area_index < 0) continue;
		
		struct HelpArea help_area = priv->help_areas[area_index];
		FOREACH_IN(HelpLine*, line, priv->help_lines) {
			if (line->align_right != align_right)
				continue;
			cairo_text_extents_t extents;
			cairo_text_extents(ctx, line->text, &extents);
			
			GdkPixbuf* pbuf = get_button_pixbuf(priv, line->scbutton, scbutton_size);
			if (pbuf != NULL) {
				cairo_save(ctx);
				int height = gdk_pixbuf_get_height(pbuf);
				if (help_area.align_right)
					cairo_translate(ctx, (int)(help_area.limits.x1 - scbutton_size),
									(int)(help_area.limits.y0 + (scbutton_size - height) * 0.5));
				else
					cairo_translate(ctx, (int)help_area.limits.x0,
									(int)(help_area.limits.y0 + (scbutton_size - height) * 0.5));
				menu_icon_draw_pixbuf(pbuf, ctx, 0, 0, &priv->color_text);
				cairo_restore(ctx);
			}
			
			cairo_save(ctx);
			// TODO: Clip to area here?
			if (help_area.align_right)
				cairo_move_to(ctx,
							(int)(help_area.limits.x1 - scbutton_size - extents.width - 2),
							// TODO: I'm not sure if this calculation makes any kind of sense
							(int)(help_area.limits.y0 + hextents.height + extents.y_bearing
									+ (scbutton_size * 0.5)));
			else
				cairo_move_to(ctx,
							(int)(help_area.limits.x0 + scbutton_size + 2),
							// TODO: Same as above
							(int)(help_area.limits.y0 + hextents.height + extents.y_bearing
									+ (scbutton_size * 0.5)));
			cairo_show_text(ctx, line->text);
			cairo_restore(ctx);
			if (help_area.limits.y0 + hextents.height > help_area.limits.y1) {
				// Can't stuff more lines to this area
				break;
			} else {
				help_area.limits.y0 += (int)(hextents.height + 2 + extents.y_bearing * 0.2);
			}
		}
	}
	
	return false;
}

static bool on_keymap_state_changed(void* keymap, void* _priv) {
	OSDKeyboardPrivate* priv = (OSDKeyboardPrivate*)_priv;
	gtk_widget_queue_draw(GTK_WIDGET(priv->draw_area));
	return false;
}


bool init_display(OSDKeyboard* kbd, OSDKeyboardPrivate* priv) {
	GError* err = NULL;
	priv->draw_area = gtk_drawing_area_new();
	priv->cursor_count = 2;
	char* cursor_filename = strbuilder_fmt("%s/images/menu-cursor.svg", scc_get_share_path());
	priv->cursors[0].image = (cursor_filename == NULL) ? NULL : gdk_pixbuf_new_from_file(cursor_filename, &err);
	free(cursor_filename);
	if (priv->cursors[0].image == NULL) {
		LERROR("Failed to load cursor image: %s", err->message);
		return false;
	}
	g_object_ref(priv->cursors[0].image);
	priv->cursors[1].image = priv->cursors[0].image;
	priv->button_images = intmap_new();
	ASSERT(priv->button_images != NULL);
	priv->keymap = gdk_keymap_get_for_display(gdk_display_get_default());
	ASSERT(priv->keymap != NULL);
	g_signal_connect(G_OBJECT(priv->keymap), "state-changed", (GCallback)&on_keymap_state_changed, priv);
	
	load_colors(priv);
	gtk_widget_set_size_request(GTK_WIDGET(priv->draw_area), priv->size.x, priv->size.y);
	g_signal_connect(G_OBJECT(priv->draw_area), "draw", (GCallback)&on_redraw, priv);
	
	GtkWidget* v = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
	gtk_widget_set_name(GTK_WIDGET(v), "osd-keyboard-container");
	gtk_widget_set_name(GTK_WIDGET(kbd), "osd-keyboard");
	gtk_container_add(GTK_CONTAINER(v), priv->draw_area);
	gtk_container_add(GTK_CONTAINER(kbd), v);
	return true;
}

