#pragma once
#include "scc/utils/dll_export.h"
#include "scc/controller.h"
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
typedef struct MenuData				MenuData;

typedef struct OSDMenuCallbacks {
	
} OSDMenuCallbacks;

typedef struct OSDMenuSettings {
	const char*			plugin_name;
	float				icon_size;
	const char*			controller_id;	// NULL for "take 1st available"
	PadStickTrigger		control_with;
	SCButton			confirm_with;
	SCButton			cancel_with;
	bool				use_cursor;
} OSDMenuSettings;

DLL_EXPORT GType osd_menu_get_type(void) G_GNUC_CONST;
DLL_EXPORT OSDMenu* osd_menu_new(const char* filename, const OSDMenuSettings* settings);
/**
 * Connects to the daemon. 'ready' or 'exit' signal is emitted to signal
 * success or failure.
 */
DLL_EXPORT void osd_menu_connect(OSDMenu* mnu);
G_END_DECLS

/** Selects either next or previous menu item */
void osd_menu_next_item(OSDMenu* mnu, int direction);

/** Selects item by index. Returns false if item at index is not selectable */
bool osd_menu_select(OSDMenu* mnu, size_t index);

// Following is list of functions exported by 'osd menu plugins'.
// Plugins are used to control how menu looks (and partially how it behaves)

#ifdef __cplusplus
extern "C" {
#endif
#include "scc/utils/dll_export.h"

/**
 * Creates GtkWidgets for menu items in OSD menu.
 * Returns parent GtkWidget of hierarchy, which will then be attached to
 * menu window.
 */
DLL_EXPORT GtkWidget* osd_menu_create_widgets(MenuData* data, OSDMenuSettings* settings);
typedef GtkWidget*(*osd_menu_create_widgets_fn)(MenuData* data, OSDMenuSettings* settings);

/**
 * Callback for "stick controller", utility that translates position of stick
 * into "keys presses". See stick_controller.c for details.
 *
 * May be undefined, in which case stick controller is not used.
 */
DLL_EXPORT void osd_menu_handle_stick(int dx, int dy, OSDMenu* mnu);
typedef void(*osd_menu_handle_stick_fn)(int dx, int dy, OSDMenu* mnu);

#ifdef __cplusplus
}
#endif

