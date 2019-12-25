#pragma once
#ifdef __cplusplus
extern "C" {
#endif
#include "scc/utils/dll_export.h"
#include "scc/controller.h"
#include "scc/menu_data.h"
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

typedef struct OSDMenuSettings {
	const char*			plugin_name;
	const char*			menu_name;
	const char*			filename;
	int					size;			// preffered number of columns/rows
	float				icon_size;
	const char*			controller_id;	// NULL for "take 1st available"
	PadStickTrigger		control_with;
	SCButton			confirm_with;
	SCButton			cancel_with;
	bool				use_cursor;
} OSDMenuSettings;


DLL_EXPORT GType osd_menu_get_type(void) G_GNUC_CONST;
DLL_EXPORT OSDMenu* osd_menu_new(const char* filename, const OSDMenuSettings* settings);
G_END_DECLS

/**
 * Connects to the daemon.
 * 'ready' or 'exit' signal is emitted to signal success or failure.
 */
DLL_EXPORT void osd_menu_connect(OSDMenu* mnu);

/** Selects either next or previous menu item */
void osd_menu_next_item(OSDMenu* mnu, int direction);

/** Selects item. Returns false if item is not selectable */
bool osd_menu_select(OSDMenu* mnu, MenuItem* item);

/**
 * Selects item by index. Returns false if index is invalid
 * or item at index is not selectable
 */
bool osd_menu_select_index(OSDMenu* mnu, size_t index);

/** Returns selected item or NULL if none is selected */
MenuItem* osd_menu_get_selected(OSDMenu* mnu);

/** Returns MenuData (list of menu items) used by this menu */
MenuData* osd_menu_get_menu_data(OSDMenu* mnu);

/** Confirms current selection in menu */
void osd_menu_confirm(OSDMenu* mnu);

/**
 * Associates random pointer with menu. If set, 'osd_menu_free_plugin_data'
 * will be called with this pointer once menu is destroyed
 */
void osd_menu_set_plugin_data(OSDMenu* mnu, void* data);

/** Returns pointer assotiated using osd_menu_set_plugin_data */
void* osd_menu_get_plugin_data(OSDMenu* mnu);

// *****************************************************************************
// Following is list of functions exported by 'osd menu plugins'.
// Plugins are used to control how menu looks and (optionaly) how it behaves

/**
 * Creates GtkWidgets for menu items in OSD menu.
 * Returns parent GtkWidget of hierarchy, which will then be attached to
 * menu window.
 */
DLL_EXPORT GtkWidget* osd_menu_create_widgets(OSDMenu* mnu, OSDMenuSettings* settings);
typedef GtkWidget*(*osd_menu_create_widgets_fn)(OSDMenu* mnu, OSDMenuSettings* settings);

/**
 * Optional callback for "stick controller", utility that translates position
 * of stick into "keys presses". See stick_controller.c for details.
 *
 * May be undefined, in which case stick controller is not used.
 */
DLL_EXPORT void osd_menu_handle_stick(OSDMenu* mnu, int dx, int dy);
typedef void(*osd_menu_handle_stick_fn)(OSDMenu* mnu, int dx, int dy);

typedef enum OSDMenuInput {
	OMI_NOT_TRANSLATED	= 0,
	OMI_CONFIRM			= 1,
	OMI_CANCEL			= 2,
	OMI_CONTROL			= 3
} OSDMenuInput;

/**
 * Optional callback replacing internal input handling.
 * 'translated_input' is button or pad/stick/trigger mapped to one of OSDMenuInput
 * enum values according to command line parameters and/or user settings.
 *
 * If defined, above stick controller is not used.
 */
DLL_EXPORT void osd_menu_handle_input(OSDMenu* mnu, SCButton button, PadStickTrigger pst, OSDMenuInput translated_input, int values[]);
typedef void(*osd_menu_handle_input_fn)(OSDMenu* mnu, SCButton button, PadStickTrigger pst, OSDMenuInput translated_input, int values[]);

/**
 * Optional callback called when menu is destoryed after 'osd_menu_set_plugin_data'
 * was used.
 */
DLL_EXPORT void osd_menu_free_plugin_data(OSDMenu* mnu, void* data);
typedef void(*osd_menu_free_plugin_data_fn)(OSDMenu* mnu, void* data);

#ifdef __cplusplus
}
#endif

