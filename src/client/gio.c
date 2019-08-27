#include "scc/utils/assert.h"
#include <glib.h> // glib.h has to be included before client.h
#include "scc/client.h"


GSource* scc_gio_client_to_gsource(SCCClient* c) {
#ifdef _WIN32
	GIOChannel* chan = g_io_channel_win32_new_socket(sccc_get_fd(c));
#else
	GIOChannel* chan = g_io_channel_unix_new(sccc_get_fd(c));
#endif
	GSource* src = g_io_create_watch(chan, G_IO_IN | G_IO_HUP);
	g_source_set_name(src, "SCCClient");
	GMainContext* ctx = g_main_context_default();
	g_source_attach(src, ctx);
	g_io_channel_unref(chan);
	return src;
}

