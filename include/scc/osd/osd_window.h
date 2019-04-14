#pragma once
#include "scc/utils/dll_export.h"
#include "scc/utils/math.h"
#include "scc/utils/rc.h"
#include <gtk/gtk.h>
#include "scc/client.h"

G_BEGIN_DECLS

#define OSD_WINDOW_TYPE (osd_window_get_type())
#define OSD_WINDOW(obj) (G_TYPE_CHECK_INSTANCE_CAST((obj), OSD_WINDOW_TYPE, OSDWindow))
#define OSD_WINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_CAST((klass), OSD_WINDOW_TYPE, OSDWindowClass))
#define IS_OSD_WINDOW(obj) (G_TYPE_CHECK_INSTANCE_TYPE((obj), OSD_WINDOW_TYPE))
#define IS_OSD_WINDOW_CLASS(klass) (G_TYPE_CHECK_CLASS_TYPE((klass), OSD_WINDOW_TYPE))
#define OSD_WINDOW_GET_CLASS(obj) (G_TYPE_INSTANCE_GET_CLASS((obj), OSD_WINDOW_TYPE, OSDWindowClass))

typedef struct _OSDWindow				OSDWindow;
typedef struct _OSDWindowClass			OSDWindowClass;

typedef struct OSDWindowCallbacks {
	
} OSDWindowCallbacks;

DLL_EXPORT GType osd_window_get_type(void) G_GNUC_CONST;
DLL_EXPORT OSDWindow* osd_window_new(const char* wmclass, const OSDWindowCallbacks callbacks);
/** Called by osd_window_new, usefull for classes derived from OSDWindow */
DLL_EXPORT void osd_window_setup(OSDWindow* osdwin, const char* wmclass, const OSDWindowCallbacks callbacks);
/** Adjusts position for currently active screen (display) */
DLL_EXPORT void osd_window_compute_position(OSDWindow* osdwin, int* x, int* y);
/**
 * Retrieves geometry of active screen (display), that is screen where
 * currently active window (not this OSDWindow) is located.
 */
DLL_EXPORT void osd_window_get_active_screen_geometry(OSDWindow* osdwin, GdkRectangle* geometry);
/**
 * Returns "osd position" set to window.
 * Note that this is _not_ actual on-screen position
 */
DLL_EXPORT ivec_t osd_window_get_position(OSDWindow* osdwin);
/** Sets "osd position" of window */
DLL_EXPORT void osd_window_set_position(OSDWindow* osdwin, int x, int y);

/**
 * Marks osd_window as done.
 * This will hide and destroy window (possibly immediatelly) and either signal
 * to scc-osd-daemon or another creator of window, or if there is no such thing,
 * exit process either immediatelly or ASAP.
 *
 * Error codes used by osd-menu, osd-message & co are as follows:
 *	 0  - clean exit, user selected option (if there was anything to select)
 *	-1  - clean exit, user canceled menu or message
 *	-2  - clean exit, menu closed from callback method
 *	-3  - clean exit, something else canceled menu (for example controller disconnected)
 *	 1  - error, invalid arguments
 *	 2  - error, failed to access sc-daemon, sc-daemon reported error or died while menu is displayed.
 *	 3  - erorr, failed to lock input stick, pad or button(s)
 *	 4  - error, request controller not connected or there is no controller connected at all
 */
DLL_EXPORT void osd_window_exit(OSDWindow* osdwin, int code);

G_END_DECLS

