/*
 * SC Controller - ParamChecker
 * 
 * Helper used to check parameters. ParamChecker is created using regex-like
 * expression and then can be used to check if ParameterList matches this expression.
 * 
 * Additionally, scc_param_checker_fill_defaults method can be used to fill optional parameters
 * with provided defaults, simplifying parsing parameters.
 * 
 * ParamChecker is meant to be allocated at start and kept in memory forever, so unlike rest of
 * project, there is little memory checking and no tools for freeing here. Should memory for
 * ParamChecker not be available, it's designed to crash.
 * 
 * Supported characters:
 *  - ' '	space - ignored
 *  - s		string
 *  - i		integer, may be followed by '8', '16' or '32' to specify range.
 *  		If not specified otherwise, 'i' means 64bit integer
 *  - u		unsigned. Has to be followed by 'i8', 'i16' or 'i32'
 *  - c		keycode. This is special case of integer in range from 1 to 0x7FFF
 *  - b		boolean. Another special case of integer, takes 0 or 1.
 *  - x		axis. This is shortcut for 'u8', for values between ABS_X and ABS_MAX, 0 to 63
 *  - f		float
 *  - a		action
 *  - r		range
 *  - .		anything. Just skipped over, not checked at all
 *
 *  - ?		marks previous parameter as optional
 *  - *		marks previous parameter as repeating, matching any (including zero) instances
 *  - +		after i16 or i32 restricts range to positive numbers. After 'x', extends range to ABS_CNT
 *  - (		in form of (min,max) specifies limit for float and integer parameter
 *
 * Example:
 *  - 'c?a'  optional integer larger than zero followed by action
 *  - 'ssi?' two strings optionaly followed by integer
*/

#pragma once
#include "scc/param_checker.h"
#include "scc/error.h"
#include <stdbool.h>
#include <stdint.h>


struct ParamData {
	ParameterType			type;
	bool					optional;
	bool					repeating;
	union {
		struct {
			int64_t			min;
			int64_t			max;
		};
		struct {
			float			fmin;
			float			fmax;
		};
		bool (*check_value)(const char* value);
	};
};


// Returns true if parameter matches paramData type and allowed range.
bool is_ok_for(Parameter* param, ParamData* data);

// Returns true if value is valid button name
bool check_button_name(const char* value);
// Returns true if value is valid axis name
bool check_axis_name(const char* value);
// Returns true if value is valid button name or is one of DEFAULT, SAME
bool check_button_name_plus(const char* value);
// Returns true if value is valid axis name or is one of DEFAULT, SAME
bool check_axis_name_plus(const char* value);

