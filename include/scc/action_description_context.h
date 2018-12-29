#pragma once
#include <stdbool.h>

typedef struct ActionDescriptionContext {
	/** on_button should be short string so it fits to button */
	bool		on_button;
	/** multiline allows string to include newline characters */
	bool		multiline;
	/** 
	 * on_osk is used by on-screen-keyboard, for buttons with on_button
	 * and for help otherwise
	 */
	bool		on_osk;
} ActionDescriptionContext;
