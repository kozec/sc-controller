#define LOG_TAG "OSD"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/osd/osd_window.h"
#include "../osd.h"
#ifdef _WIN32
	#include <windows.h>
	#include <gdk/gdkwin32.h>
#else
	#include <X11/extensions/Xfixes.h>
	#include <X11/extensions/shape.h>
	#include <X11/Xutil.h>
	#include <gdk/gdkx.h>
#endif
#include <gtk/gtk.h>
#include <stdbool.h>


static void (*gtk_window_show)(GtkWidget* w);
static void osd_window_show(GtkWidget* w);

typedef struct _OSDWindowPrivate		OSDWindowPrivate;

struct _OSDWindow {
	GtkWindow				parent;
	OSDWindowPrivate*		priv;
};

struct _OSDWindowClass {
	GtkWindowClass			parent_class;
};

struct _OSDWindowPrivate {
	struct {
		int						x;
		int						y;
	}						position;
	OSDWindowCallbacks		callbacks;
};

G_DEFINE_TYPE_WITH_CODE(OSDWindow, osd_window, GTK_TYPE_WINDOW, G_ADD_PRIVATE(OSDWindow));

static void osd_window_class_init(OSDWindowClass *klass) {
	// GObjectClass*		g_class;
	GtkWidgetClass*		w_class;
	// GParamSpec*			pspec;
	
	// g_class = G_OBJECT_CLASS(klass);
	w_class = GTK_WIDGET_CLASS(klass);

	gtk_window_show = w_class->show;
	w_class->show = &osd_window_show;
	
	g_signal_new("ready", GTK_TYPE_WINDOW, G_SIGNAL_RUN_FIRST, 0, NULL, NULL,
					g_cclosure_marshal_VOID__VOID, G_TYPE_NONE, 0);
	g_signal_new("exit", GTK_TYPE_WINDOW, G_SIGNAL_RUN_FIRST, 0, NULL, NULL,
					g_cclosure_marshal_VOID__INT, G_TYPE_NONE, 1, G_TYPE_INT);
}

static void osd_window_show(GtkWidget* widget) {
	GdkScreen* scr = gdk_screen_get_default();
	int x, y;
	gtk_widget_realize(widget);
	osd_window_compute_position(OSD_WINDOW(widget), &x, &y);
	if (x < 0)	// Negative X position is counted from right border
		x = gdk_screen_get_width(scr) - gtk_widget_get_allocated_width(widget) + x + 1;
	if (y < 0)	// Negative Y position is counted from bottom border
		y = gdk_screen_get_height(scr) - gtk_widget_get_allocated_height(widget) + y + 1;
#ifdef _WIN32
	GdkWindow* gdk_window = gtk_widget_get_window(GTK_WIDGET(widget));
	HWND hwnd = gdk_win32_window_get_handle(gdk_window);
	LONG style = GetWindowLong(hwnd, GWL_EXSTYLE);
	SetWindowLong(hwnd, GWL_EXSTYLE, style | WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_NOACTIVATE);
	SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE);
	gtk_window_show(widget);
#else
	gtk_window_show(widget);
	/*
	Display* dpy = gdk_x11_get_default_xdisplay();
	ASSERT(dpy != NULL);
	GdkWindow* gdk_window = gtk_widget_get_window(GTK_WIDGET(w));
	ASSERT(gdk_window != NULL);
	XID xid = GDK_WINDOW_XID(gdk_window);
	ASSERT(xid != 0);
	XserverRegion reg = XFixesCreateRegion(dpy, NULL, 0);
	XFixesSetWindowShapeRegion(dpy, xid, ShapeBounding, 0, 0, (XserverRegion)0);
	XFixesSetWindowShapeRegion(dpy, xid, ShapeInput, 0, 0, reg);
	XFixesDestroyRegion(dpy, reg);
	*/
#endif
	gdk_window_move(gtk_widget_get_window(widget), x, y);
}

OSDWindow* osd_window_new(const char* wmclass, const OSDWindowCallbacks callbacks) {
	GtkWidget* o = g_object_new(OSD_WINDOW_TYPE, GTK_WINDOW_TOPLEVEL, NULL);
	osd_window_setup(OSD_WINDOW(o), "osd-menu", callbacks);
	return OSD_WINDOW(o);
}

void osd_window_setup(OSDWindow* osdwin, const char* wmclass, const OSDWindowCallbacks callbacks) {
	// TODO: self.argparser = argparse.ArgumentParser(description=__doc__,
			// formatter_class=argparse.RawDescriptionHelpFormatter,
			// epilog="")
	// TODO: add_arguments()
	OSDWindowPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(osdwin, OSD_WINDOW_TYPE, OSDWindowPrivate);
	priv->callbacks = callbacks;
	// self.mainloop = None
	// priv->controller = None
	
	gtk_window_set_title(GTK_WINDOW(osdwin), wmclass);
	gtk_window_set_wmclass(GTK_WINDOW(osdwin), wmclass, wmclass);
	gtk_widget_set_name(GTK_WIDGET(osdwin), wmclass);
	gtk_window_set_decorated(GTK_WINDOW(osdwin), FALSE);
	gtk_window_stick(GTK_WINDOW(osdwin));
	gtk_window_set_skip_taskbar_hint(GTK_WINDOW(osdwin), TRUE);
	gtk_window_set_skip_pager_hint(GTK_WINDOW(osdwin), TRUE);
	gtk_window_set_keep_above(GTK_WINDOW(osdwin), TRUE);
	gtk_window_set_type_hint(GTK_WINDOW(osdwin), GDK_WINDOW_TYPE_HINT_NOTIFICATION);
}

void osd_window_exit(OSDWindow* osdwin, int code) {
	g_signal_emit_by_name(G_OBJECT(osdwin), "exit", code);
}

void osd_window_get_active_screen_geometry(OSDWindow* osdwin, GdkRectangle* geometry) {
	GdkWindow* gdkwin = gtk_widget_get_window(GTK_WIDGET(osdwin));
	GdkScreen* scr = gdk_window_get_screen(gdkwin);
	GdkWindow* awin = gdk_screen_get_active_window(scr);
	
	GdkMonitor* m;
	if (awin == NULL) {
		// Failed to find active window, grab my own monitor instead
		m = gdk_display_get_monitor_at_window(gdk_window_get_display(gdkwin), gdkwin);
	} else {
		m = gdk_display_get_monitor_at_window(gdk_window_get_display(awin), awin);
		g_object_unref(awin);
	}
	gdk_monitor_get_geometry(m, geometry);
}

void osd_window_compute_position(OSDWindow* osdwin, int* x, int* y) {
	OSDWindowPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(osdwin, OSD_WINDOW_TYPE, OSDWindowPrivate);
	GdkWindow* gdkwin = gtk_widget_get_window(GTK_WIDGET(osdwin));
	GdkRectangle geometry;
	
	osd_window_get_active_screen_geometry(osdwin, &geometry);
	int width  = gdk_window_get_width (gdkwin);
	int height = gdk_window_get_height(gdkwin);
	*x = priv->position.x;
	*y = priv->position.y;
	
	*x = (*x < 0) ? (*x + geometry.x + geometry.width - width) : (*x + geometry.x);
	*y = (*y < 0) ? (*y + geometry.y + geometry.height - height) : (geometry.y + *y);
	// to me 20 minutes from now: have fun decoding that.
}

void osd_window_set_position(OSDWindow* osdwin, int x, int y) {
	OSDWindowPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(osdwin, OSD_WINDOW_TYPE, OSDWindowPrivate);
	priv->position.x = x;
	priv->position.y = y;
}

ivec_t osd_window_get_position(OSDWindow* osdwin) {
	OSDWindowPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(osdwin, OSD_WINDOW_TYPE, OSDWindowPrivate);
	ivec_t rv = { priv->position.x, priv->position.y };
	return rv;
}

static void osd_window_init(OSDWindow* osdwin) {
	gtk_widget_set_has_window(GTK_WIDGET(osdwin), TRUE);
	install_css_provider();
	
	OSDWindowPrivate* priv = G_TYPE_INSTANCE_GET_PRIVATE(osdwin, OSD_WINDOW_TYPE, OSDWindowPrivate);
	priv->position.x = 20;
	priv->position.y = -20;
	memset(&priv->callbacks, 0, sizeof(OSDWindowCallbacks));
}

