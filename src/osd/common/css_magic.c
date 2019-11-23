#define LOG_TAG "css"
#include "scc/utils/logging.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/assert.h"
#include "scc/utils/rc.h"
#include "scc/tools.h"
#include "scc/config.h"
#include <sys/stat.h>
#include <gtk/gtk.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

static GtkCssProvider* css_provider;

static char* template_cb(const char* keyword, int* err_return, void* userdata);

struct template_data {
	Config*		config;
	char		buffer[256];
};

static bool installed = false;


void reconfigure_css_provider() {
	Config* config = config_load();
	struct template_data tdata = { config };
	StrBuilder* b = NULL;
	if (config == NULL) goto install_css_provider_fail;
	
	char* css_path = strbuilder_fmt("%s/osd_styles/%s", scc_get_share_path(), config_get(config, "osd_style"));
	if (css_path == NULL) goto install_css_provider_fail;
	DDEBUG("Loading css_provider %s", css_path);
	
	int fd = open(css_path, O_RDONLY);
	if (fd < 0) {
		LERROR("Failed to load %s: ", css_path, strerror(errno));
		free(css_path);
		return;
	}
	free(css_path);
	b = strbuilder_new();
	if (b == NULL) goto install_css_provider_fail;
	int err = strbuilder_add_fd(b, fd);
	close(fd);
	if (err < 1) {
		if (err == 0) goto install_css_provider_fail;
		strbuilder_free(b);
		LERROR("Failed to read css file: %s", strerror(err));
	}
	
	strbuilder_template(b, template_cb, NULL, NULL, &tdata);
	char* css = strbuilder_consume(b);
	RC_REL(config);
	
	GError* error = NULL;
	GtkCssProvider* new_provider = gtk_css_provider_new();
	gtk_css_provider_load_from_data(new_provider, css, strlen(css), &error);
	if (error != NULL) {
		LERROR("Failed to generate CSS provider: %s", error->message);
		g_error_free(error);
		g_object_unref(new_provider);
		return;
	}
	
	gtk_style_context_add_provider_for_screen(gdk_screen_get_default(),
			GTK_STYLE_PROVIDER(new_provider),
			GTK_STYLE_PROVIDER_PRIORITY_USER);
	
	if (css_provider != NULL) {
		gtk_style_context_remove_provider_for_screen(gdk_screen_get_default(),
				GTK_STYLE_PROVIDER(css_provider));
		g_object_unref(css_provider);
	}
	css_provider = new_provider;

	installed = true;
	return;

install_css_provider_fail:
	strbuilder_free(b);
	RC_REL(config);
	LERROR("Failed to install css provider; Out of memory.");
	return;
}

void install_css_provider() {
	if (installed) return;
	reconfigure_css_provider();
}


/** Clamps value to 0..FF range */
inline static long int clamp0xFF(long int v) {
	if (v < 0) return 0;
	if (v > 0xFF) return 0xFF;
	return v;
}

static char* template_cb(const char* keyword, int* err_return, void* _tdata) {
	struct template_data* tdata = (struct template_data*)_tdata;
	char* tmp;
	long int delta;
	char* config_kw;
	char operator = 0;
	if (strstr(keyword, "osk_") == keyword) {
		// If keyword begins with osk_, it's stored as 'osk_colors/<something>'
		config_kw = strbuilder_fmt("osk_colors/%s", &keyword[4]);
	} else {
		// Everything else is stored under 'osd_colors/<something>'
		config_kw = strbuilder_fmt("osd_colors/%s", keyword);
	}
	if (config_kw == NULL) {
		LERROR("OOM while formatting css");
		return NULL;
	}
	// This seemed like good idea in Python so now I have to implement it in
	// c as well. Color can be specified using config value _and_ with optional
	// +number / -number suffix to make color darker / lighter.
	if ((tmp = strchr(config_kw, '+')) != 0)
		operator = '+';
	else if ((tmp = strchr(config_kw, '-')) != 0)
		operator = '-';
	if (operator != 0) {
		*tmp = 0;
		delta = atol(tmp + 1);
	}
	
	char* value = (char*)config_get(tdata->config, config_kw);
	if (value == NULL) {
		WARN("Invalid keyword '%s' occured while formatting css", config_kw);
		return NULL;
	}
	free(config_kw);
	
	if (*value == '#') value ++;
	if (operator != 0) {
		long int color = strtol(value, NULL, 16);
		if (operator == '-')
			delta = -delta;
		long int r = clamp0xFF(delta + ((color & 0xFF0000) >> 16));
		long int g = clamp0xFF(delta + ((color & 0x00FF00) >> 8));
		long int b = clamp0xFF(delta + ((color & 0x0000FF)));
		snprintf(tdata->buffer, 255, "%lx%lx%lx\n", r, g, b);
		value = tdata->buffer;
	}
	
	return value;
}

