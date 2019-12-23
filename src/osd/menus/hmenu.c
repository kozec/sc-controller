/**
 * SC-Controller - Horizontal OSD Menu
 *
 * Displays all items in one row.
 * Designed mainly as RPG numeric pad display
 * and looks awfull with larger number of items.
 */
#define LOG_TAG "OSD"
#include "scc/utils/logging.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
#include "scc/osd/menu_icon.h"
#include "scc/osd/osd_menu.h"
#include "scc/menu_data.h"
#include "scc/tools.h"
#include <gtk/gtk.h>


static GtkWidget* make_menu_row(const char* icon, float size) {
	bool has_colors;
	GtkWidget* w_icon = NULL;
	if (icon != NULL) {	
		char* filename = scc_find_icon(icon, false, &has_colors, NULL, NULL);
		if (filename != NULL) {
			w_icon = GTK_WIDGET(menu_icon_new(filename, has_colors));
			free(filename);
		}
	}
	if (w_icon == NULL) {
		// If item has no icon or icon cannot be found, default "question mark" is used
		char* filename = scc_find_icon("system/unknown", false, &has_colors, NULL, NULL);
		w_icon = GTK_WIDGET(menu_icon_new(filename, has_colors));
		free(filename);
	}
	if (w_icon == NULL) {
		// If even fallback cannot be loaded, item is just skipped
		return NULL;
	}
	GtkWidget* button = gtk_button_new();
	gtk_widget_set_name(GTK_WIDGET(w_icon), "icon");
	gtk_container_add(GTK_CONTAINER(button), w_icon);
	gtk_button_set_relief(GTK_BUTTON(button), GTK_RELIEF_NONE);
	gtk_widget_set_size_request(GTK_WIDGET(button), -1, 32 + (size * 3.0));
	return button;
}


static GtkWidget* make_widget(MenuItem* i, float size) {
	GtkWidget* w;
	switch (i->type) {
	case MI_DUMMY:
	case MI_ACTION:
		w = make_menu_row(i->icon, size);
		if (i->type == MI_DUMMY)
			gtk_widget_set_name(w, "osd-menu-dummy");
		else
			gtk_widget_set_name(w, "osd-menu-item");
		break;
	case MI_SUBMENU:
		w = make_menu_row(i->icon, size);
		gtk_widget_set_name(GTK_WIDGET(w), "osd-menu-item");
		break;
	case MI_SEPARATOR:
		// horizontal menu ignores separators
		return NULL;
	default:
		return NULL;
	}
	g_object_set_data(G_OBJECT(w), "scc-menu-item-data", i);
	return w;
}


DLL_EXPORT GtkWidget* osd_menu_create_widgets(OSDMenu* mnu, OSDMenuSettings* settings) {
	MenuData* data = osd_menu_get_menu_data(mnu);
	GtkWidget* v = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
	
	ListIterator it = iter_get(data);
	FOREACH(MenuItem*, i, it) {
		GtkWidget* w = make_widget(i, settings->icon_size);
		if (w != NULL) {
			gtk_box_pack_start(GTK_BOX(v), w, false, true, 0);
			i->userdata = w;
		}
	}
	iter_free(it);
	return v;
}

DLL_EXPORT void osd_menu_handle_stick(OSDMenu* mnu, int dx, int dy) {
	osd_menu_next_item(mnu, dx);
}

