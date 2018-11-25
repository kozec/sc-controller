#pragma once
#include <gtk/gtk.h>

G_BEGIN_DECLS

#define OSD_MENU_TYPE (osd_menu_get_type())
#define OSD_MENU(obj) (G_TYPE_CHECK_INSTANCE_CAST((obj), OSD_MENU_TYPE, OSDMenu))
#define OSD_MENU_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST((klass), OSD_MENU_TYPE, OSDMenuClass))
#define IS_OSD_MENU(obj) (G_TYPE_CHECK_INSTANCE_TYPE((obj), OSD_MENU_TYPE))
#define IS_OSD_MENU_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE((klass), OSD_MENU_TYPE))
#define OSD_MENU_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS((obj), OSD_MENU_TYPE, OSDMenuClass))

typedef struct _OSDMenu				OSDMenu;
typedef struct _OSDMenuClass		OSDMenuClass;

typedef struct OSDMenuCallbacks {
	
} OSDMenuCallbacks;

GType osd_menu_get_type(void) G_GNUC_CONST;
OSDMenu* osd_menu_new(const char* filename);

G_END_DECLS
