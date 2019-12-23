#define LOG_TAG "OSD"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/osd/menu_icon.h"
#include "../osd.h"
#include <gdk-pixbuf/gdk-pixbuf.h>
#include <gtk/gtk.h>
#include <stdbool.h>


typedef struct _MenuIconPrivate		MenuIconPrivate;

struct _MenuIcon {
	GtkDrawingArea					parent;
	MenuIconPrivate*				priv;
};

struct _MenuIconClass {
	GtkDrawingAreaClass				parent_class;
};

struct _MenuIconPrivate {
	GdkPixbuf*						pb;
	bool							has_colors;
};

G_DEFINE_TYPE_WITH_CODE(MenuIcon, menu_icon, GTK_TYPE_DRAWING_AREA, G_ADD_PRIVATE(MenuIcon));

static void menu_icon_class_init(MenuIconClass *klass) { }

static void on_allocated(GtkWidget* widget, GdkRectangle* allocation, gpointer data) {
	if (allocation->width < allocation->height)
		gtk_widget_set_size_request(widget, allocation->height, -1);
}

GdkPixbuf* menu_icon_get_pixbuf(MenuIcon* w) {
	MenuIconPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(w, MENU_ICON_TYPE, MenuIconPrivate);
	return priv->pb;
}

void menu_icon_draw_pixbuf(GdkPixbuf* pb, cairo_t* target, guint width, guint height, const GdkRGBA* color) {
	if (pb == NULL) return;
	cairo_surface_t* surf = NULL;
	GdkPixbuf* scaled = NULL;
	if ((width > 0) && (height > 0)) {
		scaled = gdk_pixbuf_scale_simple(pb, width, height, GDK_INTERP_BILINEAR);
		surf = scaled == NULL ? NULL : gdk_cairo_surface_create_from_pixbuf(scaled, 1, NULL);
		if ((scaled == NULL) || (surf == NULL)) {
			LERROR("OOM while scaling icon");
			if (surf != NULL) cairo_surface_destroy(surf);
			if (scaled != NULL) gdk_pixbuf_unref(scaled);
			return;
		}
	} else {
		surf = gdk_cairo_surface_create_from_pixbuf(pb, 1, NULL);
		if (surf == NULL) {
			LERROR("OOM while drawing icon");
			return;
		}
	}
	if (color == NULL) {
		gdk_cairo_set_source_pixbuf(target, (scaled != NULL) ? scaled : pb, 0, 0);
		// cairo_set_source_surface(target, surf, 0, 0);
		// cairo_rectangle(target, 0, 0, width, height);
		cairo_paint(target);
	} else {
		gdk_cairo_set_source_rgba(target, color);
		cairo_mask_surface(target, surf, 0, 0);
	}
	cairo_surface_destroy(surf);
	if (scaled != NULL)
		gdk_pixbuf_unref(scaled);
}

static bool on_draw(GtkWidget* widget, cairo_t* cr, gpointer data) {
	MenuIconPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(widget, MENU_ICON_TYPE, MenuIconPrivate);
	GtkStyleContext* context = gtk_widget_get_style_context(widget);
	guint width = gtk_widget_get_allocated_width(widget);
	guint height = gtk_widget_get_allocated_height(widget);
	
	gtk_render_background (context, cr, 0, 0, width, height);
	if (priv->pb != NULL) {
		if (priv->has_colors) {
			menu_icon_draw_pixbuf(priv->pb, cr, width, height, NULL);
		} else {
			GdkRGBA color;
			gtk_style_context_get_color(context, GTK_STATE_FLAG_NORMAL, &color);
			menu_icon_draw_pixbuf(priv->pb, cr, width, height, &color);
		}
	}
	return false;
}


static bool on_destroy(GtkWidget *widget, gpointer data) {
	MenuIconPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(widget, MENU_ICON_TYPE, MenuIconPrivate);
	if (priv->pb != NULL) {
		gdk_pixbuf_unref(priv->pb);
		priv->pb = NULL;
	}
	return false;
}

bool menu_icon_set_filename(MenuIcon* mi, const char* filename) {
	MenuIconPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mi, MENU_ICON_TYPE, MenuIconPrivate);
	GError* err = NULL;
	if (priv->pb != NULL) {
		gdk_pixbuf_unref(priv->pb);
		priv->pb = NULL;
	}
	priv->pb = gdk_pixbuf_new_from_file(filename, &err);
	if (err != NULL) {
		LERROR("Failed to load icon: %s (code %i)", err->message, err->code);
		g_error_free(err);
		return false;
	}
	return true;
}

void menu_icon_set_has_colors(MenuIcon* mi, bool has_colors) {
	MenuIconPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(mi, MENU_ICON_TYPE, MenuIconPrivate);
	priv->has_colors = has_colors;
}

MenuIcon* menu_icon_new(const char* file_name, bool has_colors) {
	GtkWidget* o = g_object_new(MENU_ICON_TYPE, NULL);
	MenuIconPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(o, MENU_ICON_TYPE, MenuIconPrivate);
	memset(priv, 0, sizeof(MenuIconPrivate));
	g_signal_connect(G_OBJECT(o), "draw", G_CALLBACK(on_draw), NULL);
	g_signal_connect(G_OBJECT(o), "size-allocate", G_CALLBACK(on_allocated), NULL);
	g_signal_connect(G_OBJECT(o), "destroy", G_CALLBACK(on_destroy), NULL);
	if (file_name != NULL)
		menu_icon_set_filename(MENU_ICON(o), file_name);
	menu_icon_set_has_colors(MENU_ICON(o), has_colors);
	return MENU_ICON(o);
}

static void menu_icon_init(MenuIcon* mi) { }

