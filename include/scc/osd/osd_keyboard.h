#pragma once
#include "scc/utils/dll_export.h"
#include "scc/utils/rc.h"
#include <gtk/gtk.h>

G_BEGIN_DECLS

#define OSD_KEYBOARD_TYPE (osd_keyboard_get_type())
#define OSD_KEYBOARD(obj) (G_TYPE_CHECK_INSTANCE_CAST((obj), OSD_KEYBOARD_TYPE, OSDKeyboard))
#define OSD_KEYBOARD_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST((klass), OSD_KEYBOARD_TYPE, OSDKeyboardClass))
#define IS_OSD_KEYBOARD(obj) (G_TYPE_CHECK_INSTANCE_TYPE((obj), OSD_KEYBOARD_TYPE))
#define IS_OSD_KEYBOARD_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE((klass), OSD_KEYBOARD_TYPE))
#define OSD_KEYBOARD_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS((obj), OSD_KEYBOARD_TYPE, OSDKeyboardClass))

typedef struct _OSDKeyboard				OSDKeyboard;
typedef struct _OSDKeyboardClass		OSDKeyboardClass;

typedef struct OSDKeyboardCallbacks {
	
} OSDKeyboardCallbacks;

DLL_EXPORT GType osd_keyboard_get_type(void) G_GNUC_CONST;
DLL_EXPORT OSDKeyboard* osd_keyboard_new(const char* filename);

G_END_DECLS

