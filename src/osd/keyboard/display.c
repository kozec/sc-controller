#define LOG_TAG "OSD"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
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

/*
static gboolean osd_keyboard_on_data_ready(GIOChannel* source, GIOCondition condition, gpointer _kbd) {
	OSDKeyboard* kbd = OSD_KEYBOARD(_kbd);
	OSDKeyboardPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(kbd, OSD_KEYBOARD_TYPE, OSDKeyboardPrivate);
	const char* message = sccc_recieve(priv->client);
	if (message != NULL) {
		if (message[0] == 0)
			// Disconnected
			// TODO: Handle this
			return false;
		// if (message != NULL)
		// 	LOG("> %s", message);
	}
	// on_reconfigured
	return true;
}

static void osd_keyboard_connection_ready(SCCClient* c) {
	OSDKeyboard* kbd = OSD_KEYBOARD(c->userdata);
	OSDKeyboardPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(kbd, OSD_KEYBOARD_TYPE, OSDKeyboardPrivate);
	uint32_t handle = sccc_get_controller_handle(c, priv->controller_id);
	if (handle == 0) {
		if (priv->controller_id == NULL)
			LERROR("There is no controller connected");
		else
			LERROR("Requested controller '%s' not connected", priv->controller_id);
		osd_window_exit(OSD_WINDOW(kbd), 4);
		return;
	}
	
	// if (!sccc_lock(c, handle, control_with, confirm_with, cancel_with)) {
	// 	LERROR("Failed to lock controller");
	// 	osd_window_exit(OSD_WINDOW(kbd), 3);
	// }
}

static void osd_keyboard_on_event(SCCClient* c, uint32_t handle, SCButton button, PadStickTrigger pst, int values[]) {
	// OSDKeyboard* kbd = OSD_KEYBOARD(c->userdata);
	// OSDKeyboardPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(kbd, OSD_KEYBOARD_TYPE, OSDKeyboardPrivate);
	// if (pst == priv->control_with)
	// 	stick_controller_feed(priv->sc, values);
	// else if ((button == priv->cancel_with) && (values[0]))
	// 	osd_window_exit(OSD_WINDOW(kbd), -1);
	// else if ((button == priv->confirm_with) && (values[0])) {
	// 	osd_keyboard_item_selected(kbd);
	// 	osd_window_exit(OSD_WINDOW(kbd), 0);
	// }
	// else
	// 	LOG("# %i %i %i > %i %i", handle, button, pst, values[0], values[1]);
}
*/

inline static void button_as_path(cairo_t* ctx, Button* b) {
	cairo_move_to(ctx, b->pos.x, b->pos.y);
	cairo_rel_line_to(ctx, b->size.x, 0);
	cairo_rel_line_to(ctx, 0, b->size.y);
	cairo_rel_line_to(ctx, -b->size.x, 0);
	cairo_rel_line_to(ctx, 0, -b->size.y);
}

bool on_redraw(GtkWidget* draw_area, cairo_t* ctx, void* _priv) {
	OSDKeyboardPrivate* priv = (OSDKeyboardPrivate*)_priv;
	StrBuilder* label = strbuilder_new();
	cairo_font_extents_t fextents;
	ASSERT(priv->draw_area == draw_area);
#ifndef _WIN32
	XkbStateRec xkb_state;
	Display* dpy = gdk_x11_get_default_xdisplay();
	XkbGetState(dpy, XkbUseCoreKbd, &xkb_state);
#endif
	// GtkStyleContext* stylectx = gtk_widget_get_style_context (draw_area);
	// guint width = gtk_widget_get_allocated_width (draw_area);
	// guint height = gtk_widget_get_allocated_height (draw_area);
	
	
	// TODO: It would be cool to use user-set font here, but cairo doesn't
	// have glyph replacement and most of default fonts (Ubuntu, Cantarell,
	// similar shit) misses pretty-much everything but letters, notably ↲
	//
	// For that reason, DejaVu Sans is hardcoded for now. On systems
	// where DejaVu Sans is not available, Cairo will automatically fallback
	// to default font.
	cairo_select_font_face(ctx, "DejaVu Sans", 0, 0); // CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_NORMAL);
	cairo_set_line_width(ctx, LINE_WIDTH);
	cairo_set_font_size(ctx, FONT_SIZE);
	cairo_font_extents(ctx, &fextents);
	
	// Buttons
	ListIterator it = iter_get(priv->buttons);
	ASSERT(it != NULL);
	FOREACH(Button*, b, it) {
		if (b->pressed)
			gdk_cairo_set_source_rgba(ctx, &priv->color_pressed);
		else if (b->hilighted)
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
		
		// label
		if ((b->keycode) || (b->label)) {
			strbuilder_clear(label);
#ifndef _WIN32
			if (b->keycode) {
				// LOG(" >> current group: %i", xkb_state.group);
				guint mt = gdk_keymap_get_modifier_state(priv->keymap);
				GdkModifierType consumed_modifiers;
				// gint effective_group, level;
				guint keyval;
				bool translated = gdk_keymap_translate_keyboard_state(
							priv->keymap, scc_keycode_to_x11(b->keycode),
							mt, xkb_state.group, &keyval, NULL, NULL,
							&consumed_modifiers);
				guint32 unicode = gdk_keyval_to_unicode(keyval);
				// TODO: Maybe use images
				if (unicode == 8)
					strbuilder_addf(label, "←");
				else if (unicode == 13)
					strbuilder_addf(label, "↲");
				else if ((translated) && (unicode > 32)) // 32 = space
					strbuilder_addf(label, "%lc", unicode);
			}
#endif
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
	iter_free(it);
	
	for (int side=0; side<=1; side++) {
		cairo_save(ctx);
		cairo_translate(ctx, 10 + side * 80, 20);
		gdk_cairo_set_source_pixbuf(ctx, priv->cursor_images[side], 0, 0);
		cairo_paint(ctx);
		cairo_restore(ctx);
	}
	
	/*
	# Overlay
	Gdk.cairo_set_source_pixbuf(ctx, self.overlay.get_pixbuf(), 0, 0)
	ctx.paint()
	
	# Help
	ctx.set_source_rgba(*self.color_text)
	ctx.set_font_size(16)
	ascent, descent, height, max_x_advance, max_y_advance = ctx.font_extents()
	for left_right in (0, 1):
		x, y, w, h = self._help_areas[left_right]
		lines = self._help_lines[left_right]
		xx = x if left_right == 0 else x + w
		yy = y
		for (icon, line) in lines:
			yy += height
			if yy > y + h:
				break
			image = self.get_button_image(icon, height * 0.9)
			if image is None: continue
			iw, ih = image.get_width(), image.get_height()
			
			if left_right == 1:	# Right align
				extents = ctx.text_extents(line)
				x_bearing, y_bearing, width, trash, x_advance, y_advance = extents
				ctx.save()
				ctx.translate(xx - height + (height - iw) * 0.5,
					1 + yy - (ascent + ih) * 0.5)
				Gdk.cairo_set_source_pixbuf(ctx, image, 0, 0)
				ctx.paint()
				ctx.restore()
				ctx.move_to(xx - x_bearing - width - 5 - height, yy)
			else:
				ctx.save()
				ctx.translate(1 + xx + (height - iw) * 0.5,
					1 + yy - (ascent + ih) * 0.5)
				Gdk.cairo_set_source_pixbuf(ctx, image, 0, 0)
				ctx.paint()
				ctx.restore()
				ctx.move_to(xx + 5 + height, yy)
				
			ctx.show_text(line)
			ctx.stroke()
	*/
	
	return false;
}

static bool on_keymap_state_changed(void* keymap, void* _priv) {
	OSDKeyboardPrivate* priv = (OSDKeyboardPrivate*)_priv;
	gtk_widget_queue_draw(GTK_WIDGET(priv->draw_area));
}


bool init_display(OSDKeyboard* kbd, OSDKeyboardPrivate* priv) {
	GError* err = NULL;
	priv->draw_area = gtk_drawing_area_new();
	priv->cursor_count = 2;
	vec_set(priv->cursors[0], 0, 0);
	vec_set(priv->cursors[1], 0, 0);
	char* cursor_filename = strbuilder_fmt("%s/images/menu-cursor.svg", scc_get_share_path());
	priv->cursor_images[0] = (cursor_filename == NULL) ? NULL : gdk_pixbuf_new_from_file(cursor_filename, &err);
	if (priv->cursor_images[0] == NULL) {
		free(cursor_filename);
		LERROR("Failed to load cursor image: %s", err->message);
		return false;
	}
	free(cursor_filename);
	g_object_ref(priv->cursor_images[0]);
	priv->cursor_images[1] = priv->cursor_images[0];
#ifdef _WIN32
	priv->keymap = NULL;
#else
	priv->keymap = gdk_keymap_get_for_display(gdk_display_get_default());
	ASSERT(priv->keymap != NULL);
	g_signal_connect(G_OBJECT(priv->keymap), "state-changed", (GCallback)&on_keymap_state_changed, priv);
#endif
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

