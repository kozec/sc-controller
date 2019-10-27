/**
 * SC-Controller - Grid Menu
 *
 * Displays items in (as rectangluar as possible - and
 * that's usually not very much) grid.
 */
#define LOG_TAG "OSD"
#include "scc/utils/logging.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
#include "scc/utils/math.h"
#include "scc/osd/menu_icon.h"
#include "scc/osd/osd_menu.h"
#include "scc/menu_data.h"
#include "scc/tools.h"
#include <gtk/gtk.h>


struct GridMenuData {
	size_t items_per_row;
};


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
			gtk_widget_set_name(w, "osd-menu-item-big-icon");
		break;
	case MI_SUBMENU: {
		w = make_menu_row(i->icon, size);
		gtk_widget_set_name(GTK_WIDGET(w), "osd-menu-item-big-icon");
		break;
	}
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
	GtkWidget* v = gtk_grid_new();
	
	ListIterator it = iter_get(data);
	size_t size = scc_menudata_len(data);
	size_t items_per_row = 1;
	if (settings->size > 1) {
		items_per_row = settings->size;
	} else {
		// Make best attempt at square
		items_per_row = 1 + (int)sqrt((double)max(1, size - 1));
		// Handle some common case specifically
		if (size == 6) items_per_row = 3;
		if (size == 8) items_per_row = 4;
	}
	int x = 0, y = 0;
	FOREACH(MenuItem*, i, it) {
		GtkWidget* w = make_widget(i, settings->icon_size);
		if (w != NULL) {
			gtk_grid_attach(GTK_GRID(v), w, x, y, 1, 1);
			i->userdata = w;
			x ++;
			if (x >= items_per_row) {
				x = 0;
				y ++;
			}
		}
	}
	iter_free(it);
	struct GridMenuData* plugin_data = malloc(sizeof(struct GridMenuData));
	if (plugin_data != NULL) {
		plugin_data->items_per_row = items_per_row;
		osd_menu_set_plugin_data(mnu, plugin_data);
	}
	return v;
}

DLL_EXPORT void osd_menu_handle_stick(OSDMenu* mnu, int dx, int dy) {
	if (dx != 0)
		osd_menu_next_item(mnu, dx);
	else if (dy != 0) {
		struct GridMenuData* plugin_data = osd_menu_get_plugin_data(mnu);
		if (plugin_data == NULL) // Shouldn't happen unless OOM
			return;
		for (size_t i=0; i<plugin_data->items_per_row; i++)
			osd_menu_next_item(mnu, dy);
	}
}


DLL_EXPORT void osd_menu_free_plugin_data(OSDMenu* mnu, void* data) {
	free(data);
}

