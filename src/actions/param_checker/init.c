#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/param_checker.h"
#include "scc/conversions.h"
#include "scc/parameter.h"
#include "scc/error.h"
#include "param_checker.h"
#include <stdbool.h>
#include <string.h>
#include <limits.h>
#include <float.h>
#include <stdlib.h>

typedef LIST_TYPE(ParamData) ParamDataList;
#define MAX_RANGE_SIZE	16


static inline ParamData* PD(ParameterType type) {
	ParamData* d = malloc(sizeof(ParamData));
	ASSERT(d != NULL);
	d->type = type;
	d->optional = false;
	d->repeating = false;
	d->min = LONG_MIN;
	d->max = LONG_MAX;
	return d;
}


void scc_param_checker_init(ParamChecker* pc, const char* expression) {
	ParamDataList lst = list_new(ParamData, 0);
	ParamData* last;
	bool unsignedint = false;
	
	ASSERT(lst != NULL);
	ASSERT(INT_MAX == 2147483647);
	ASSERT(((int64_t)INT_MIN - 1) == -2147483649);
	
	char* i = (char*)expression;
	char* end = i + strlen(i);
	for (; i<end; i++) {
		switch (*i) {
		case '?':
		case '*':
			if (list_len(lst) < 1)
				FATAL("Unexpected '%c' in ParamChecker specification", *i);
			last = list_last(lst);
			if (last->repeating || last->optional)
				FATAL("'*' and '?' cannot be used at once in ParamChecker specification");
			last->optional = true;
			if (*i == '*')
				last->repeating = true;
			break;
		case '(': {
			char range[MAX_RANGE_SIZE];
			size_t k = 0;
			if (list_len(lst) < 1)
				FATAL("Unexpected '%c' in ParamChecker specification", *i);
			last = list_last(lst);
			if (last->type != PT_INT)
				FATAL("'(' after non-numeric in ParamChecker specification");
			for (++i; i<end; i++) {
				range[k++] = *i;
				if (k >= MAX_RANGE_SIZE)
					FATAL("Range number too long in ParamChecker specification");
				if (*i == ')') {
					range[k-1] = 0;
					last->max = atoi(range);
					break;
				} else if (*i == ',') {
					range[k-1] = 0;
					last->min = atoi(range);
					k = 0;
				} else if ((*i != ',') && !((*i >= '0') && (*i <= '9'))) {
					FATAL("Invalid character '%c' in ParamChecker range specification", *i);
				}
			}
			if (*i != ')')
				FATAL("'(' without ')' in ParamChecker specification");
			break;
		}
		case '+':
			if ((list_len(lst) > 0) && (list_last(lst)->type == PT_INT)) {
				last = list_last(lst);
				last->min = 0;
				if (last->max == ABS_MAX)
					last->max = ABS_CNT;
			} else if ((list_len(lst) > 0) && (list_last(lst)->type == PT_FLOAT)) {
				last = list_last(lst);
				last->fmin = 0;
			} else if ((list_len(lst) > 0) && (list_last(lst)->type == PT_STRING)) {
				last = list_last(lst);
				if (last->check_value == check_button_name)
					last->check_value = check_button_name_plus;
				else if (last->check_value == check_axis_name)
					last->check_value = check_axis_name_plus;
				else
					FATAL("Unexpected '+' in ParamChecker specification");
			} else {
				FATAL("Unexpected '+' in ParamChecker specification");
			}
			break;
		case '.':
			list_add(lst, PD(PT_ANY));
			break;
		case 's':
		case 'A':
		case 'B':
			list_add(lst, PD(PT_STRING));
			last = list_last(lst);
			if (*i == 'B')
				last->check_value = check_button_name;
			else if (*i == 'A')
				last->check_value = check_axis_name;
			else
				last->check_value = NULL;
			break;
		case 'c':
			list_add(lst, PD(PT_INT));
			last = list_last(lst);
			last->min = 1; last->max = USHRT_MAX;
			break;
		case 'b':
			list_add(lst, PD(PT_INT));
			last = list_last(lst);
			last->min = 0; last->max = 1;
			break;
		case 'x':
			list_add(lst, PD(PT_INT));
			last = list_last(lst);
			// TODO: Use ABS_MAX here.
			last->min = 0; last->max = ABS_MAX;
			break;
		case 'a':
			list_add(lst, PD(PT_ACTION));
			break;
		case 'r':
			list_add(lst, PD(PT_RANGE));
			break;
		case 'f':
			list_add(lst, PD(PT_FLOAT));
			last = list_last(lst);
			last->fmin = FLT_MAX * -1.0; last->fmax = FLT_MAX;
			break;
		case 'i':
			list_add(lst, PD(PT_INT));
			last = list_last(lst);
			if (*(i+1) == '8') {
				i ++;				// skip over 'i'
				if (!unsignedint)
					FATAL("Signed i8 is not supported in ParamChecker specification");
				last->min = 0; last->max = 0xFF;
			} else if ((*(i+1) == '1') && (*(i+2) == '6')) {
				last->min = (unsignedint) ? 0         : SHRT_MIN;
				last->max = (unsignedint) ? USHRT_MAX : SHRT_MAX;
				i += 2;				// skip over '16'
			} else if ((*(i+1) == '3') && (*(i+2) == '2')) {
				last->min = (unsignedint) ? 0        : INT_MIN;
				last->max = (unsignedint) ? UINT_MAX : INT_MAX;
				i += 2;				// skip over '32'
			} else if (unsignedint) {
				FATAL("'u' has to be followed by 'i8', 'i16' or 'i32' in ParamChecker specification");
			}
			unsignedint = false;
			break;
		case 'u':
			if (*(i+1) != 'i')
				FATAL("'u%c' makes no sense in ParamChecker specification", *(i+1));
			unsignedint = true;
			break;
		case ' ':
		case '\t':
			// ignored
			break;
		default:
			FATAL("Unexpected '%c' in ParamChecker specification", *i);
		}
	}
	
	pc->length = list_len(lst);
	pc->data = (ParamData**)list_consume(lst);
	pc->defaults_count = 0;
	pc->defaults = NULL;
}
