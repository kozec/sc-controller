#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/utils/tokenizer.h"
#include "scc/utils/rc.h"
#include "scc/action.h"
#include "scc/parser.h"
#include "scc/error.h"
#include "../src/parser/parser.h"
#include <string.h>
#include <stdlib.h>
#include <math.h>

/**
 * Basically just tests if "None" can be parsed.
 * This was 1st test made and is kept here out of nostalgy.
 */
void test_none(CuTest* tc) {
	ActionOE a = scc_parse_action("None");
	assert_msg(tc, !IS_ACTION_ERROR(a), ACTION_ERROR(a)->message);
	char* s = scc_action_to_string(ACTION(a));
	assert(tc, strcmp(s, "None") == 0);
	assert(tc, ACTION(a) == NoAction);
	free(s);
	OE_REL(a);
}


void test_param_parser_none(CuTest* tc) {
	Tokens* t = tokenize("None");
	ParamOE p = scc_parse_parameter(t);
	tokens_free(t);
	assert_msg(tc, !IS_PARAM_ERROR(p), PARAM_ERROR(p)->message);
	assert(tc, PARAMETER(p) == None);
	OE_REL(p);
}


void test_param_parser_int(CuTest* tc) {
	Tokens* t = tokenize("42");
	ParamOE p = scc_parse_parameter(t);
	tokens_free(t);
	assert_msg(tc, !IS_PARAM_ERROR(p), PARAM_ERROR(p)->message);
	Parameter* param = PARAMETER(p);
	assert(tc, param->type == PT_INT);
	assert(tc, scc_parameter_as_int(param) == 42);
	assert(tc, scc_parameter_as_float(param) == 42.0);
	char* str = scc_parameter_to_string(param);
	assert(tc, strcmp(str, "42") == 0);
	free(str);
	OE_REL(p);
}


void test_param_parser_float(CuTest* tc) {
	Tokens* t = tokenize("4.2");
	ParamOE p = scc_parse_parameter(t);
	tokens_free(t);
	assert_msg(tc, !IS_PARAM_ERROR(p), PARAM_ERROR(p)->message);
	Parameter* param = PARAMETER(p);
	assert(tc, param->type == PT_FLOAT);
	assert(tc, scc_parameter_as_int(param) == 4);
	assert(tc, fabs(4.2f - scc_parameter_as_float(param)) < 0.001);
	char* str = scc_parameter_to_string(param);
	assert(tc, strcmp(str, "4.2") == 0);
	free(str);
	OE_REL(p);
}


/** Test various ways string can confuse tokenizer */
void test_tokenizing_strings(CuTest* tc) {
	Tokens* t = tokenize("'ab\\'c' 'ab c'\"abc\"'\\t\\\\n \\r'");
	assert(tc, strcmp(iter_next(t), "'ab\'c'") == 0);
	assert(tc, strcmp(iter_next(t), " ") == 0);
	assert(tc, strcmp(iter_next(t), "'ab c'") == 0);
	assert(tc, strcmp(iter_next(t), "\"abc\"") == 0);
	assert(tc, strcmp(iter_next(t), "'\t\\\n \r'") == 0);
	tokens_free(t);
}


/** Test parsing string parameter along with escaping and unescaping */
void test_param_parser_string(CuTest* tc) {
	Tokens* t = tokenize("\"abcd \\\\efgh\"");
	ParamOE p = scc_parse_parameter(t);
	tokens_free(t);
	assert_msg(tc, !IS_PARAM_ERROR(p), PARAM_ERROR(p)->message);
	Parameter* param = PARAMETER(p);
	assert(tc, param->type == PT_STRING);
	assert(tc, strcmp(scc_parameter_as_string(param), "abcd \\efgh") == 0);
	assert(tc, strcmp(scc_parameter_to_string(param), "\'abcd \\\\efgh\'") == 0);
	
	OE_REL(p);
}


/** Tests parsing valid syntax but invalid action keyword */
void test_invalid_action(CuTest* tc) {
	ActionOE a;
	a = scc_parse_action("notabutton(11, KEY_A, REL_B)");
	assert(tc, IS_ACTION_ERROR(a));
	assert(tc, strcmp(ACTION_ERROR(a)->message, "Unexpected: 'notabutton'"));
}


#define COMPARE_ACTION_TO_STR(a, str) do {							\
	assert_msg(tc, !IS_ACTION_ERROR(a), ACTION_ERROR(a)->message);	\
	char* astr = scc_action_to_string(ACTION(a));					\
	assert(tc, strcmp(astr, str) == 0);								\
	RC_REL(ACTION(a));												\
	free(astr);														\
} while(0)


/** Test parsing of "button" along with some basic parser features */
void test_button(CuTest* tc) {
	ActionOE a;
	a = scc_parse_action("button(11)");
	COMPARE_ACTION_TO_STR(a, "button(11)");
	
	a = scc_parse_action("button(KEY_A)");
	COMPARE_ACTION_TO_STR(a, "button(KEY_A)");
	
	a = scc_parse_action("button(KEY_A, 12)");
	COMPARE_ACTION_TO_STR(a, "button(KEY_A, 12)");
	
	a = scc_parse_action("button(Keys.KEY_A)");
	COMPARE_ACTION_TO_STR(a, "button(KEY_A)");
}


void test_feedback(CuTest* tc) {
	ActionOE a;
	a = scc_parse_action("feedback(LEFT, button(11))");
	COMPARE_ACTION_TO_STR(a, "feedback(LEFT, button(11))");
	
	a = scc_parse_action("feedback(LEFT, 10, button(11))");
	COMPARE_ACTION_TO_STR(a, "feedback(LEFT, 10, button(11))");
	
	// Fix: Conflating compatible types breaks when parameters are turned
	//      to string and then parsed back to action.
	a = scc_parse_action("feedback(LEFT, 256, 14.8, button(11))");
	COMPARE_ACTION_TO_STR(a, "feedback(LEFT, 256, 14.8, button(11))");
}


/** Test parsing of "xy", as it is nice example of action that takes another action as parameter */
void test_xy(CuTest* tc) {
	ActionOE a;
	a = scc_parse_action("XY(button(11))");
	COMPARE_ACTION_TO_STR(a, "XY(button(11))");
	
	a = scc_parse_action("XY(axis(Axes.ABS_RX), raxis(Axes.ABS_RY, -100, 300))");
	COMPARE_ACTION_TO_STR(a, "XY(axis(ABS_RX), raxis(ABS_RY, -100, 300))");
}


/** Tests parsing of "dpad" */
void test_dpad(CuTest* tc) {
	ActionOE a;
	a = scc_parse_action("hatup(Axes.ABS_HAT0Y)");
	COMPARE_ACTION_TO_STR(a, "hatup(ABS_HAT0Y)");
	
	a = scc_parse_action("dpad(hatup(Axes.ABS_HAT0Y), hatdown(Axes.ABS_HAT0Y), hatleft(Axes.ABS_HAT0X), hatright(Axes.ABS_HAT0X))");
	COMPARE_ACTION_TO_STR(a, "dpad(hatup(ABS_HAT0Y), hatdown(ABS_HAT0Y), hatleft(ABS_HAT0X), hatright(ABS_HAT0X))");
}


/** Tests parsing of macro */
void test_macro(CuTest* tc) {
	ActionOE a;
	a = scc_parse_action("button(Keys.KEY_Q); button(KEY_W);button(KEY_E)");
	COMPARE_ACTION_TO_STR(a, "button(KEY_Q); button(KEY_W); button(KEY_E)");
}


/** Tests parsing of string with newline in it */
void test_multiline(CuTest* tc) {
	ActionOE a = scc_parse_action("mode(\nA, button(Keys.KEY_Q),\nB, button(KEY_W))");
	assert_msg(tc, !IS_ACTION_ERROR(a), ACTION_ERROR(a)->message);
	COMPARE_ACTION_TO_STR(a, "mode(A, button(KEY_Q), B, button(KEY_W))");
}


/** Tests case that failed in past */
void test_axis0(CuTest* tc) {
	ActionOE a;
	a = scc_parse_action("axis(0)");
	COMPARE_ACTION_TO_STR(a, "axis(0)");
}


/** Tests case that failed in past */
void test_menu_w_default(CuTest* tc) {
	ActionOE a = scc_parse_action("menu('Default.menu',DEFAULT,B,A)");
	assert_msg(tc, !IS_ACTION_ERROR(a), ACTION_ERROR(a)->message);
	a = scc_parse_action("menu('Default.menu',3)");
	assert_msg(tc, !IS_ACTION_ERROR(a), ACTION_ERROR(a)->message);
}


/** Tests case that failed in past */
void test_gyro(CuTest* tc) {
	ActionOE a = scc_parse_action("gyroabs(Rels.REL_Y, None, Rels.REL_X)");
	assert_msg(tc, !IS_ACTION_ERROR(a), ACTION_ERROR(a)->message);
	COMPARE_ACTION_TO_STR(a, "gyroabs(REL_Y, None, REL_X)");
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_none);
	DEFAULT_SUITE_ADD(test_param_parser_none);
	DEFAULT_SUITE_ADD(test_param_parser_int);
	DEFAULT_SUITE_ADD(test_param_parser_float);
	DEFAULT_SUITE_ADD(test_param_parser_string);
	DEFAULT_SUITE_ADD(test_tokenizing_strings);
	DEFAULT_SUITE_ADD(test_invalid_action);
	DEFAULT_SUITE_ADD(test_button);
	DEFAULT_SUITE_ADD(test_feedback);
	DEFAULT_SUITE_ADD(test_xy);
	DEFAULT_SUITE_ADD(test_dpad);
	DEFAULT_SUITE_ADD(test_macro);
	DEFAULT_SUITE_ADD(test_axis0);
	DEFAULT_SUITE_ADD(test_gyro);
	DEFAULT_SUITE_ADD(test_multiline);
	DEFAULT_SUITE_ADD(test_menu_w_default);
	
	return CuSuiteRunDefault();
}

