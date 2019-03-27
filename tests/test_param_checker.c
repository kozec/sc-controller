#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/param_checker.h"
#include "scc/parameter.h"
#include "scc/action.h"
#include "../src/actions/param_checker/param_checker.h"
#include <string.h>
#include <limits.h>
#include <stdint.h>
#include <stdlib.h>

#define ASSERT_OK(...) assert(tc, scc_param_checker_check(&pc, "test", scc_make_param_list(__VA_ARGS__)) == NULL)
#define _ASSERT_ERR_CODE(c, ...)	err = scc_param_checker_check(&pc, "test", scc_make_param_list(__VA_ARGS__)); \
									assert(tc, (err!=NULL) && (err->code == c))
#define ASSERT_INVALID_TYPE(...)	_ASSERT_ERR_CODE(AEC_INVALID_PARAMETER_TYPE, __VA_ARGS__)
#define ASSERT_OUT_OF_RANGE(...)	_ASSERT_ERR_CODE(AEC_PARAMETER_OUT_OF_RANGE, __VA_ARGS__)
#define ASSERT_BAD_PARAM_CNT(...)	_ASSERT_ERR_CODE(AEC_INVALID_NUMBER_OF_PARAMETERS, __VA_ARGS__)
#define ASSERT_IN_ERROR(str, ...)	err = scc_param_checker_check(&pc, "test", scc_make_param_list(__VA_ARGS__)); \
									assert(tc, (err!=NULL) && (strstr(err->message, str) != NULL));

// Note: Tests here leaks a lot of memory.
// Mostly because I'm lazy.
// Plus, leaks is not what's tested here.

void test_types(CuTest* tc) {
	ParamChecker pc;
	ParamError* err;
	Parameter* s = scc_new_const_string("test");
	Parameter* c = scc_new_int_parameter(42);
	Parameter* i = scc_new_int_parameter(0x5FFFF);
	Parameter* f = scc_new_float_parameter(0.42);
	Parameter* a = scc_new_action_parameter(NoAction);
	Parameter* r = scc_new_range_parameter(scc_new_int_parameter(0x35), RT_LESS, 13.0);
	
	scc_param_checker_init(&pc, "s");
	ASSERT_OK(s);
	ASSERT_INVALID_TYPE(i);
	ASSERT_INVALID_TYPE(f);
	ASSERT_INVALID_TYPE(r);
	ASSERT_INVALID_TYPE(a);

	scc_param_checker_init(&pc, "i");
	ASSERT_OK(i);
	ASSERT_OK(c);
	ASSERT_OK(f);
	ASSERT_INVALID_TYPE(s);
	ASSERT_INVALID_TYPE(r);
	ASSERT_INVALID_TYPE(a);
	
	scc_param_checker_init(&pc, "c");
	ASSERT_OUT_OF_RANGE(i);
	ASSERT_OK(c);
	ASSERT_OUT_OF_RANGE(f);
	ASSERT_INVALID_TYPE(s);
	ASSERT_INVALID_TYPE(r);
	ASSERT_INVALID_TYPE(a);
	
	scc_param_checker_init(&pc, "f");
	ASSERT_OK(i);
	ASSERT_OK(c);
	ASSERT_OK(f);
	ASSERT_INVALID_TYPE(s);
	ASSERT_INVALID_TYPE(r);
	ASSERT_INVALID_TYPE(a);
	
	scc_param_checker_init(&pc, "a");
	ASSERT_OK(a);
	ASSERT_INVALID_TYPE(i);
	ASSERT_INVALID_TYPE(c);
	ASSERT_INVALID_TYPE(f);
	ASSERT_INVALID_TYPE(c);
	ASSERT_INVALID_TYPE(r);
	
	scc_param_checker_init(&pc, "r");
	ASSERT_OK(r);
	ASSERT_INVALID_TYPE(i);
	ASSERT_INVALID_TYPE(c);
	ASSERT_INVALID_TYPE(f);
	ASSERT_INVALID_TYPE(c);
	ASSERT_INVALID_TYPE(a);
}


// Tests various versions of unsigned integer
void test_uints(CuTest* tc) {
	ParamChecker pc;
	ParamError* err;
	
	// sanity check (mostly mine...)
	assert(tc, INT_MAX == 2147483647);
	assert(tc, ((int64_t)INT_MIN - 1) == -2147483649);
	
	scc_param_checker_init(&pc, "ui8");
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter(-1));
	ASSERT_OK(scc_new_int_parameter(0));
	ASSERT_OK(scc_new_int_parameter(42));
	ASSERT_OK(scc_new_int_parameter(0xFF));
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter(0x100));
	
	scc_param_checker_init(&pc, "ui16");
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter(-1));
	ASSERT_OK(scc_new_int_parameter(0));
	ASSERT_OK(scc_new_int_parameter((int64_t)USHRT_MAX));
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter((int64_t)USHRT_MAX+1));
	
	scc_param_checker_init(&pc, "ui32");
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter(-1));
	ASSERT_OK(scc_new_int_parameter(0));
	ASSERT_OK(scc_new_int_parameter((int64_t)UINT_MAX));
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter((int64_t)UINT_MAX + 1));
}


// Tests various versions of signed integer
void test_ints(CuTest* tc) {
	ParamChecker pc;
	ParamError* err;
	
	// There is no i8
	
	scc_param_checker_init(&pc, "i16");
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter((int64_t)SHRT_MIN - 1));
	ASSERT_OK(scc_new_int_parameter((int64_t)SHRT_MIN));
	ASSERT_OK(scc_new_int_parameter(-1));
	ASSERT_OK(scc_new_int_parameter(0));
	ASSERT_OK(scc_new_int_parameter((int64_t)SHRT_MAX));
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter((int64_t)SHRT_MAX + 1));
		
	scc_param_checker_init(&pc, "i32");
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter((int64_t)INT_MIN - 1));
	ASSERT_OK(scc_new_int_parameter((int64_t)INT_MIN));
	ASSERT_OK(scc_new_int_parameter(-1));
	ASSERT_OK(scc_new_int_parameter(0));
	ASSERT_OK(scc_new_int_parameter((int64_t)INT_MAX));
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter((int64_t)INT_MAX + 1));
}


// Tests i16+, i32+, 'c' and 'x'.
void test_int_plus(CuTest* tc) {
	ParamChecker pc;
	ParamError* err;
	
	scc_param_checker_init(&pc, "i16+");
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter(-1));
	ASSERT_OK(scc_new_int_parameter(0));
	ASSERT_OK(scc_new_int_parameter((int64_t)SHRT_MAX));
	
	scc_param_checker_init(&pc, "i32+");
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter(-1));
	ASSERT_OK(scc_new_int_parameter(0));
	ASSERT_OK(scc_new_int_parameter((int64_t)INT_MAX));
	
	scc_param_checker_init(&pc, "c");
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter(-1));
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter(0));
	ASSERT_OK(scc_new_int_parameter(1));
	ASSERT_OK(scc_new_int_parameter((int64_t)SHRT_MAX));
	
	scc_param_checker_init(&pc, "x");
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter(-1));
	ASSERT_OK(scc_new_int_parameter(0));
	ASSERT_OK(scc_new_int_parameter(62));
	ASSERT_OK(scc_new_int_parameter(63));
	ASSERT_OUT_OF_RANGE(scc_new_int_parameter(64));
}


// Tests if correct number is reported when invalid parameter is supplied
void test_arg_numer(CuTest* tc) {
	ParamChecker pc;
	ParamError* err;
	Parameter* i = scc_new_int_parameter(42);
	Parameter* o = scc_new_int_parameter(0xFFFFFFFFFFFFFFF);
	Parameter* s = scc_new_const_string("string");
	
	// 1st
	scc_param_checker_init(&pc, "ii");
	ASSERT_IN_ERROR("1st", s, i);
	scc_param_checker_init(&pc, "ci");
	ASSERT_IN_ERROR("1st", o, i);
	// 2nd
	scc_param_checker_init(&pc, "ii");
	ASSERT_IN_ERROR("2nd", i, s);
	scc_param_checker_init(&pc, "ic");
	ASSERT_IN_ERROR("2nd", i, o);
	// 2nd after optional
	scc_param_checker_init(&pc, "i?i");
	ASSERT_IN_ERROR("2nd", i, s);
	scc_param_checker_init(&pc, "i?c");
	ASSERT_IN_ERROR("2nd", i, o);
	// Non-filled optionals, not enough params to fill what's required
	scc_param_checker_init(&pc, "i?i?sss");
	ASSERT_IN_ERROR("Invalid number", s, s);
}

// Tests if correct number is reported when invalid parameter is supplied
void test_optionals(CuTest* tc) {
	ParamChecker pc;
	ParamError* err;
	Parameter* i = scc_new_int_parameter(42);
	Parameter* s = scc_new_const_string("string");
	Parameter* big = scc_new_int_parameter((uint64_t)LONG_MAX);
	
	// Leading optionals
	scc_param_checker_init(&pc, "c?i?s");
	ASSERT_OK(i, i, s);								// All there
	ASSERT_OK(i, s);								// 1st ommited
	ASSERT_OK(s);									// Both ommited
	ASSERT_OUT_OF_RANGE(big, s);					// Out of range for 1st

	// Trailing optionals
	scc_param_checker_init(&pc, "isc?i?");
	
	ASSERT_OK(i, s, i, big);						// All there
	ASSERT_OK(i, s, i);								// Last ommited
	ASSERT_OK(i, s);								// Both ommited
	ASSERT_OUT_OF_RANGE(i, s, big);					// Out of range for last
	
	// Optionals in middle (should NOT be used anywhere)
	scc_param_checker_init(&pc, "scs?c?ii");
	ASSERT_OK(s, i, s, i, big, i);					// All there
	ASSERT_OK(s, i, i, i, big);						// String is missing
	// Next one fails as 1st 'i' after 's' fills optional parameter
	// and so there is no parameter for last 'i'
	ASSERT_BAD_PARAM_CNT(s, i, s, i, i);
	// Next one is same case, but 'i' can't fill for missing
	// parameter as it expects action type
	scc_param_checker_init(&pc, "scs?a?ii");
	ASSERT_OK(s, i, s, i, big);
	
	// Combining wrong types with optionals
	scc_param_checker_init(&pc, "ia?sc");
	ASSERT_OK(i, s, i);								// Action missing
	ASSERT_IN_ERROR("2nd parameter", i, i, s, i);	// 'i' used instead of action
	ASSERT_IN_ERROR("2nd parameter", i, i, i);		// Everything is wrong here
	ASSERT_IN_ERROR("3rd parameter", i, s, big);	// 2nd is ommited and 4th is out of range
	
	// Too much shit after optional
	scc_param_checker_init(&pc, "i?ss");
	ASSERT_OK(i, s, s);								// OK
	ASSERT_OK(s, s);								// OK
	ASSERT_BAD_PARAM_CNT(i, s, s, s);				// Not OK
	ASSERT_BAD_PARAM_CNT(s, s, s);					// Seriously not OK
}


void test_repeat(CuTest* tc) {
	ParamChecker pc;
	ParamError* err;
	Parameter* r = scc_new_range_parameter(scc_new_int_parameter(0x35), RT_LESS, 13.0);
	Parameter* a = scc_new_action_parameter(NoAction);
	Parameter* i = scc_new_int_parameter(0x5FFFF);
	Parameter* s = scc_new_const_string("test");
	
	// Take any number of actions
	scc_param_checker_init(&pc, "a*");
	ASSERT_OK(a);									// Just one
	ASSERT_OK(a, a);								// Two
	ASSERT_OK(a, a, a, a, a, a, a, a, a, a);		// A lot
	ASSERT_IN_ERROR("1st parameter", i);			// Just invalid
	ASSERT_BAD_PARAM_CNT(a, a, i);					// Two OK, one invalid
	ASSERT_BAD_PARAM_CNT(a, i, a);					// One OK, one invalid, then one OK
	
	// Take any number of actions followed by integer
	scc_param_checker_init(&pc, "a*i");
	ASSERT_OK(a, i);								// Just one
	ASSERT_OK(a, a, a, a, i);						// A lot
	ASSERT_OK(i);									// Action is missing
	ASSERT_BAD_PARAM_CNT(a);						// Int is missing
	
	// At least one action followed by integer
	scc_param_checker_init(&pc, "aa*i");
	ASSERT_OK(a, i);								// Just one
	ASSERT_OK(a, a, a, a, a, i);					// A lot
	ASSERT_IN_ERROR("1st parameter", i);			// Just invalid
	ASSERT_BAD_PARAM_CNT(a);						// Two OK, one invalid
	ASSERT_BAD_PARAM_CNT(a, a);						// One OK, one invalid, then one OK
	
	// Star argument followed by optional
	scc_param_checker_init(&pc, "a*i?");
	ASSERT_OK(NULL);								// Nothing is fine too
	ASSERT_OK(a);									// No int
	ASSERT_OK(i);									// No action
	ASSERT_IN_ERROR("1st parameter", s);			// Nonsense
	ASSERT_IN_ERROR("2nd parameter", a, s);			// Nonsense as 2nd
	
	// Star argument followed by optional and then required
	scc_param_checker_init(&pc, "a*i?r");
	ASSERT_BAD_PARAM_CNT(NULL);						// Nothing is not fine
	ASSERT_OK(r);									// Only required
	ASSERT_OK(a, r);								// No int
	ASSERT_OK(i, r);								// No action
	ASSERT_IN_ERROR("2nd parameter", a, s);			// Nonsense
	
}

void test_fill_defaults(CuTest* tc) {
	Parameter* a = scc_new_action_parameter(scc_button_action_from_keycode(0x11));
	Parameter* i = scc_new_int_parameter(15);
	ParameterList params;
	ParamChecker pc;
	
	scc_param_checker_init(&pc, "i?i?aaa");
	scc_param_checker_set_defaults(&pc, 42, 43);
	params = scc_param_checker_fill_defaults(&pc, scc_make_param_list(a, a, a));
	assert(tc, scc_parameter_as_int(params->items[0]) == 42);
	assert(tc, scc_parameter_as_int(params->items[1]) == 43);
	params = scc_param_checker_fill_defaults(&pc, scc_make_param_list(i, a, a, a));
	assert(tc, scc_parameter_as_int(params->items[0]) == 15);
	assert(tc, scc_parameter_as_int(params->items[1]) == 43);
	
	// Defaults at end
	scc_param_checker_init(&pc, "aai?s?");
	scc_param_checker_set_defaults(&pc, 42, "ok");
	params = scc_param_checker_fill_defaults(&pc, scc_make_param_list(a, a));
	assert(tc, scc_parameter_as_int(params->items[2]) == 42);
	assert(tc, strcmp(scc_parameter_as_string(params->items[3]), "ok") == 0);
	
	// Defaults on both sides
	scc_param_checker_init(&pc, "i?aas?");
	scc_param_checker_set_defaults(&pc, 42, "ok");
	params = scc_param_checker_fill_defaults(&pc, scc_make_param_list(a, a));
	assert(tc, scc_parameter_as_int(params->items[0]) == 42);
	assert(tc, strcmp(scc_parameter_as_string(params->items[3]), "ok") == 0);
	
	// All defaults
	scc_param_checker_init(&pc, "i?a?s?");
	scc_param_checker_set_defaults(&pc, 42, NoAction, "ok");
	params = scc_param_checker_fill_defaults(&pc, scc_make_param_list(NULL));
	assert(tc, list_len(params) == 3);
	
	// Default before star argument
	scc_param_checker_init(&pc, "i?aa*");
	scc_param_checker_set_defaults(&pc, 42);
	params = scc_param_checker_fill_defaults(&pc, scc_make_param_list(a, a, a, a, a));
	assert(tc, scc_parameter_as_int(params->items[0]) == 42);
	assert(tc, list_len(params) == 6);

	// Default after star argument
	scc_param_checker_init(&pc, "aa*i?");
	scc_param_checker_set_defaults(&pc, 42);
	params = scc_param_checker_fill_defaults(&pc, scc_make_param_list(a, a, a, a, a));
	assert(tc, scc_parameter_as_int(params->items[5]) == 42);
	assert(tc, list_len(params) == 6);
}

/** Tests reference counting when fill defaults is used */
void test_rc(CuTest* tc) {
	Action* a = scc_button_action_from_keycode(0x11);
	Parameter* i = scc_new_int_parameter(15);
	ParameterList params;
	ParamChecker pc;
	
	scc_param_checker_init(&pc, "i?a");
	scc_param_checker_set_defaults(&pc, 42);
	
	// Initially, 'a' should have single reference
	assert(tc, a->_rc.count == 1);
	Parameter* p = scc_new_action_parameter(a);
	// Parameter 'p' now holds one reference to action 'a'.
	// Creating lst bellow doesn't change that
	assert(tc, a->_rc.count == 2);
	ParameterList lst = scc_make_param_list(p);
	assert(tc, p->_rc.count == 2);	// one for me and one for list
	
	// fill defaults adds reference to parameter 'p', but not to action 'a'
	ParameterList filled = scc_param_checker_fill_defaults(&pc, lst);
	assert(tc, p->_rc.count == 3);	// me, list and 'filled' list
	assert(tc, a->_rc.count == 2);
	
	// freeing 'filled' list should get back to state before fill_defaults
	list_free(filled);
	assert(tc, p->_rc.count == 2);
	assert(tc, a->_rc.count == 2);
	// freeing 'lst' should leave parameter 'p' with single reference
	list_free(lst);
	assert(tc, p->_rc.count == 1);
	assert(tc, a->_rc.count == 2);
	
	// Now same thing with use of 'i' parameter as well
	assert(tc, i->_rc.count == 1);
	assert(tc, p->_rc.count == 1);
	lst = scc_make_param_list(i, p);
	assert(tc, a->_rc.count == 2);
	assert(tc, i->_rc.count == 2);
	assert(tc, p->_rc.count == 2);
	
	filled = scc_param_checker_fill_defaults(&pc, lst);
	assert(tc, p->_rc.count == 3);
	assert(tc, i->_rc.count == 3);
	assert(tc, a->_rc.count == 2);
	
	list_free(filled);
	assert(tc, p->_rc.count == 2);
	assert(tc, i->_rc.count == 2);
	assert(tc, a->_rc.count == 2);
	
	list_free(lst);
	assert(tc, p->_rc.count == 1);
	assert(tc, i->_rc.count == 1);
	assert(tc, a->_rc.count == 2);
	
	// Finall cleanup
	RC_REL(p);
	RC_REL(i);
	assert(tc, a->_rc.count == 1);
	RC_REL(a);
}

/*

// Tests specifications used by actual actions
func TestActions(t *testing.T) {
	a := NewActionParameter(construct_button_from_keycode(0x11))
	i := NewIntegerParameter(42)
	
	var c ParamChecker
	// dpad4
	c = dpad4_param_checker
	assertOK(t, c.Check("test", []Parameter{a}))
	assertOK(t, c.Check("test", []Parameter{a,a,a}))
	assertOK(t, c.Check("test", []Parameter{a,a,a,a}))
	assertError(t, "Invalid number", c.Check("test", []Parameter{a,a,a,a,a}))
	
	// dpad8
	c = dpad8_param_checker
	assertOK(t, c.Check("test", []Parameter{a}))
	assertOK(t, c.Check("test", []Parameter{a,a,a}))
	assertOK(t, c.Check("test", []Parameter{a,a,a,a}))
	assertOK(t, c.Check("test", []Parameter{a,a,a,a,a}))
	assertOK(t, c.Check("test", []Parameter{a,a,a,a,a,a,a}))							// 7
	assertOK(t, c.Check("test", []Parameter{a,a,a,a,a,a,a,a}))							// 8
	assertError(t, "Invalid number", c.Check("test", []Parameter{a,a,a,a,a,a,a,a,a}))	// 9
	assertError(t, "3rd parameter", c.Check("test", []Parameter{a,a,i}))
	assert(t, len(c.FillDefaults([]Parameter{})) == 9)
	
	// ring (uses range limit)
	c = ring_param_checker
	assertOK(t, c.Check("test", []Parameter{a}))
	assertOK(t, c.Check("test", []Parameter{NewFloatParameter(0.1), a}))
	assertOK(t, c.Check("test", []Parameter{NewFloatParameter(0.5), a}))
	assertOK(t, c.Check("test", []Parameter{NewFloatParameter(0.9), a}))
	assertError(t, "out of range", c.Check("test", []Parameter{NewFloatParameter(0.09), a}))
	assertError(t, "out of range", c.Check("test", []Parameter{NewFloatParameter(0.91), a}))
	
	// mouse (uses nil as default for '.')
	c = mouse_param_checker
	assert(t, len(c.FillDefaults([]Parameter{})) == 2)
	assert(t, c.FillDefaults([]Parameter{})[0] == NoParameter)
	assert(t, c.FillDefaults([]Parameter{})[0].Type() == PTNone)
}
*/


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_types);
	DEFAULT_SUITE_ADD(test_uints);
	DEFAULT_SUITE_ADD(test_ints);
	DEFAULT_SUITE_ADD(test_int_plus);
	DEFAULT_SUITE_ADD(test_arg_numer);
	DEFAULT_SUITE_ADD(test_optionals);
	DEFAULT_SUITE_ADD(test_repeat);
	DEFAULT_SUITE_ADD(test_fill_defaults);
	DEFAULT_SUITE_ADD(test_rc);
	
	return CuSuiteRunDefault();
}
