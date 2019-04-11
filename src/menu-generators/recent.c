#include "scc/menu_generator.h"
#include "scc/bindings.h"
#include "scc/config.h"


const ParamDescription* get_parameters(size_t* size_return) {
	static ParamDescription pds[] = {
		{ PT_INT, "Number of items to generate" },
		{ 0, NULL },
	};
	return pds;
}


void generate(GeneratorContext* ctx) {
	Config* cfg = ctx->get_config(ctx);
	
	// Check parameter
	size_t count = 5;
	if (ctx->get_parameter(ctx, 0) != NULL) {
		Parameter* p = ctx->get_parameter(ctx, 0);
		if (p->type == PT_INT)
			count = scc_parameter_as_int(p);
		else
			return;			// invalid parameters
	}
	if (count < 1) count = 1;
	if (count > 20) count = 20;
	
	// Grab recent profiles
	const char** recents = malloc(sizeof(char*) * count);
	if (recents == NULL)
		return;				// OOM
	size_t real_cunt = config_get_strings(cfg, "recent_profiles", recents, count);
	
	// Generate menu items
	for (size_t i=0; i<real_cunt; i++) {
		Parameter* profile = profile = scc_new_string_parameter(recents[i]);
		if (profile == NULL)
			goto scc_menu_generator_get_items_oom;
		Parameter* action_params[] = { profile };
		ActionOE action = scc_action_new_from_array("profile", 1, action_params);
		RC_REL(profile);
		if ((action.error->flag & AF_ERROR) != 0) {
			RC_REL(action.error);
			goto scc_menu_generator_get_items_oom;
		}
		if (!ctx->add_action(ctx, recents[i], NULL, action.action))
			RC_REL(action.action);
	}
	free(recents);
	return;
	
scc_menu_generator_get_items_oom:
	free(recents);
}

