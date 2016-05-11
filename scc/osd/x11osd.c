#include <Python.h>

#include <X11/Xlib.h>
#include <X11/Xutil.h>
#include <X11/extensions/Xcomposite.h>
#include <X11/extensions/Xfixes.h>
#include <X11/extensions/shape.h>


void allow_input_passthrough (Display *dpy, Window w) {
	XserverRegion region = XFixesCreateRegion (dpy, NULL, 0);
 
	XFixesSetWindowShapeRegion (dpy, w, ShapeBounding, 0, 0, 0);
	XFixesSetWindowShapeRegion (dpy, w, ShapeInput, 0, 0, region);

	XFixesDestroyRegion (dpy, region);
}


void make_window_clicktrough(Display *dpy, Window win) {
	
	int scr = XDefaultScreen(dpy);
	Window root = DefaultRootWindow (dpy);

	XClassHint* hint = XAllocClassHint();
	XGetClassHint(dpy, win, hint);

	printf("Hello! %p  @ %s %s\n", dpy, hint->res_name, hint->res_class);

	allow_input_passthrough (dpy, win);
}

