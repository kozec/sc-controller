#define LOG_TAG "OSD"
#include "scc/utils/logging.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
#include "scc/osd/menu_icon.h"
#include "scc/osd/osd_menu.h"
#include "scc/menu_data.h"
#include "scc/tools.h"
#include <gtk/gtk.h>


static void align_cb(GtkWidget* w, void* align) {
	if (G_OBJECT_TYPE(w) == GTK_TYPE_LABEL)
		gtk_label_set_xalign(GTK_LABEL(w), *(gfloat*)align);
}


static GtkWidget* make_menu_row(const char* label, const char* icon, bool is_submenu) {
	bool has_colors;
	GtkWidget* w_icon = NULL;
	if (icon != NULL) {	
		char* filename = scc_find_icon(icon, false, &has_colors, NULL, NULL);
		if (filename != NULL) {
			w_icon = GTK_WIDGET(menu_icon_new(filename, has_colors));
			free(filename);
		}
	}
	GtkWidget* label1 = gtk_label_new(label);
	GtkWidget* label2 = is_submenu ? gtk_label_new(">>") : NULL;
	GtkWidget* box = gtk_box_new(GTK_ORIENTATION_HORIZONTAL, 0);
	GtkWidget* button = gtk_button_new();
	gtk_label_set_xalign(GTK_LABEL(label1), 0.0);
	if (w_icon != NULL) {
		gtk_box_pack_start(GTK_BOX(box), w_icon, false, true, 0);
		gtk_box_pack_start(GTK_BOX(box), label1, true, true, 10);
		gtk_widget_set_name(GTK_WIDGET(w_icon), "icon");
	} else {
		gtk_box_pack_start(GTK_BOX(box), label1, true, true, 1);
	}
	if (label2 != NULL) {
		gtk_widget_set_margin_start(label2, 30);
		gtk_label_set_xalign(GTK_LABEL(label2), 1.0);
		gtk_box_pack_start(GTK_BOX(box), label2, false, true, 1);
	}
	gtk_container_add(GTK_CONTAINER(button), box);
	gtk_button_set_relief(GTK_BUTTON(button), GTK_RELIEF_NONE);
	return button;
}


static GtkWidget* make_widget(MenuItem* i) {
	GtkWidget* w;
	gfloat center = 0.5;
	switch (i->type) {
	case MI_DUMMY:
	case MI_ACTION:
		if (i->name == NULL) {
			// TODO: Use description instead
			if (i->action == NULL)
				return NULL;
			char* label = scc_action_to_string(i->action);
			ASSERT(label != NULL);
			w = make_menu_row(label, i->icon, false);
			free(label);
		} else {
			w = make_menu_row(i->name, i->icon, false);
		}
		if (i->type == MI_DUMMY)
			gtk_widget_set_name(w, "osd-menu-dummy");
		else
			gtk_widget_set_name(w, "osd-menu-item");
		break;
	case MI_SUBMENU:
		if (i->submenu == NULL)
			// Shouldn't be possible
			return NULL;
		if (i->name == NULL) {
			char* name = scc_path_strip_extension(i->submenu);
			ASSERT(name != NULL);
			w = make_menu_row(name, i->icon, true);
			free(name);
		} else {
			w = make_menu_row(i->name == NULL ? i->submenu : i->name, i->icon, true);
		}
		gtk_widget_set_name(GTK_WIDGET(w), "osd-menu-item");
		break;
	case MI_SEPARATOR:
		if (i->name != NULL) {
			w = gtk_button_new_with_label(i->name);
			gtk_button_set_relief(GTK_BUTTON(w), GTK_RELIEF_NONE);
			gtk_container_forall(GTK_CONTAINER(w), align_cb, &center);
		} else {
			w = gtk_separator_new(GTK_ORIENTATION_HORIZONTAL);
		}
		gtk_widget_set_name(GTK_WIDGET(w), "osd-menu-separator");
		break;
	default:
		return NULL;
	}
	g_object_set_data(G_OBJECT(w), "scc-menu-item-data", i);
	return w;
}


DLL_EXPORT GtkWidget* osd_menu_create_widgets(OSDMenu* mnu, OSDMenuSettings* settings) {
	MenuData* data = osd_menu_get_menu_data(mnu);
	GtkWidget* v = gtk_box_new(GTK_ORIENTATION_VERTICAL, 0);
	
	ListIterator it = iter_get(data);
	FOREACH(MenuItem*, i, it) {
		GtkWidget* w = make_widget(i);
		if (w != NULL) {
			gtk_box_pack_start(GTK_BOX(v), w, false, true, 0);
			i->userdata = w;
		}
	}
	iter_free(it);
	return v;
}

DLL_EXPORT void osd_menu_handle_stick(OSDMenu* mnu, int dx, int dy) {
	osd_menu_next_item(mnu, dy);
}

