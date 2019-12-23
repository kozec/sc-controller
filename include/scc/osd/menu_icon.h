#pragma once
#include "scc/utils/dll_export.h"
#include "scc/utils/rc.h"
#include <gtk/gtk.h>
#include "scc/client.h"

G_BEGIN_DECLS

#define MENU_ICON_TYPE (menu_icon_get_type())
#define MENU_ICON(obj) (G_TYPE_CHECK_INSTANCE_CAST((obj), MENU_ICON_TYPE, MenuIcon))
#define MENU_ICON_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST((klass), MENU_ICON_TYPE, MenuIconClass))
#define IS_MENU_ICON(obj) (G_TYPE_CHECK_INSTANCE_TYPE((obj), MENU_ICON_TYPE))
#define IS_MENU_ICON_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE((klass), MENU_ICON_TYPE))
#define MENU_ICON_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS((obj), MENU_ICON_TYPE, MenuIconClass))

typedef struct _MenuIcon					MenuIcon;
typedef struct _MenuIconClass			MenuIconClass;

DLL_EXPORT GType menu_icon_get_type(void) G_GNUC_CONST;
DLL_EXPORT MenuIcon* menu_icon_new(const char* file_name, bool has_colors);
DLL_EXPORT bool menu_icon_set_filename(MenuIcon* mi, const char* filename);
DLL_EXPORT void menu_icon_set_has_colors(MenuIcon* mi, bool has_colors);
/** Returns internal pixbuf of menu icon, without increasing reference counter */
DLL_EXPORT GdkPixbuf* menu_icon_get_pixbuf(MenuIcon* mi);
/**
 * Draws GdkPixbuf* to cairo context.
 * This can be used to draw any image in same way as recolored icons in menus are.
 *
 * 'color' may be NULL, in which case image is just rescaled on the fly
 * and drawn with colors.
 * 'width' (or 'height') may be 0, in which case image is nor rescaled
 * (but may be recolored)
 */
DLL_EXPORT void menu_icon_draw_pixbuf(GdkPixbuf* pb, cairo_t* target, guint width, guint height, const GdkRGBA* color);

G_END_DECLS

