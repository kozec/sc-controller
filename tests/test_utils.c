#include "CuTest.h"
#include "scc/utils/traceback.h"
#include "scc/utils/strbuilder.h"
#include "scc/utils/iterable.h"
#include "scc/utils/hashmap.h"
#include "scc/utils/intmap.h"
#include "scc/utils/list.h"
#include <string.h>
#include <stdlib.h>


void test_list(CuTest* tc) {
	StringList sl = list_new(char, 2);
	assert(tc, sl != NULL);
	assert(tc, list_size(sl) == 0);
	list_add(sl, "Hello");
	list_add(sl, "World");
	assert(tc, list_size(sl) == 2);
	list_add(sl, "Items over");
	list_add(sl, "originally allocated");
	list_add(sl, "size");
	assert(tc, list_size(sl) == 5);
	assert(tc, strcmp(list_get(sl, 0), "Hello") == 0);
	assert(tc, strcmp(list_get(sl, 4), "size") == 0);
	list_free(sl);
}

void test_list_insert(CuTest* tc) {
	StringList sl = list_new(char, 2);
	assert(tc, sl != NULL);
	assert(tc, list_size(sl) == 0);
	list_add(sl, "Hello");
	list_add(sl, "World");
	assert(tc, list_size(sl) == 2);
	
	list_insert(sl, 1, "Inserted item 1");
	assert(tc, strcmp(list_get(sl, 0), "Hello") == 0);
	assert(tc, strcmp(list_get(sl, 1), "Inserted item 1") == 0);
	
	list_insert(sl, 0, "Inserted item 0");
	assert(tc, strcmp(list_get(sl, 0), "Inserted item 0") == 0);
	assert(tc, strcmp(list_get(sl, 1), "Hello") == 0);
	assert(tc, strcmp(list_get(sl, 2), "Inserted item 1") == 0);
	
	list_insert(sl, 2, "Inserted item 2");
	assert(tc, strcmp(list_get(sl, 0), "Inserted item 0") == 0);
	assert(tc, strcmp(list_get(sl, 1), "Hello") == 0);
	assert(tc, strcmp(list_get(sl, 2), "Inserted item 2") == 0);
	assert(tc, strcmp(list_get(sl, 3), "Inserted item 1") == 0);
	assert(tc, strcmp(list_get(sl, 4), "World") == 0);
	
	list_insert(sl, 99, "Added item");
	assert(tc, strcmp(list_get(sl, 4), "World") == 0);
	assert(tc, strcmp(list_get(sl, 5), "Added item") == 0);
	
	assert(tc, list_size(sl) == 6);
	list_free(sl);
}

bool test_filter_fn(void* item, void *userdata) {
	return 0 != strcmp(item, userdata);
}

void test_list_filter(CuTest* tc) {
	StringList sl = list_new(char, 2);
	list_add(sl, "Hello");
	list_add(sl, "World");
	list_add(sl, "Item 1");
	list_add(sl, "Item 2");
	list_add(sl, "Last Item");
	
	list_filter(sl, &test_filter_fn, "World");
	
	assert(tc, strcmp(list_get(sl, 0), "Hello") == 0);
	assert(tc, strcmp(list_get(sl, 1), "Item 1") == 0);
	assert(tc, strcmp(list_get(sl, 3), "Last Item") == 0);
	
	list_free(sl);
}

void test_list_iterator(CuTest* tc) {
	StringList sl = list_new(char, 2);
	list_add(sl, "Randm");
	list_add(sl, "List_");
	list_add(sl, "_of__");
	list_add(sl, "_some");
	list_add(sl, "five_");
	list_add(sl, "chars");
	list_add(sl, "_long");
	list_add(sl, "texts");
	
	ListIterator iter = iter_get(sl);
	assert(tc, strcmp(iter_next(iter), "Randm") == 0);
	assert(tc, strcmp(iter_next(iter), "List_") == 0);
	for (int i=0; i<5; i++) iter_next(iter); // Skip from 'of' to '_long'
	assert(tc, strcmp(iter_next(iter), "texts") == 0);
	assert(tc, !iter_has_next(iter));
	iter_free(iter);
	
	iter = iter_get(sl);
	size_t total = 0;
	FOREACH(const char*, i, iter) {
		total += strlen(i);
	}
	iter_free(iter);
	assert(tc, total == 40);
	list_free(sl);
}

void test_list_for_in(CuTest* tc) {
	StringList sl = list_new(char, 2);
	size_t total = 0;
	// Check iterating over empty list
	FOREACH_IN(char*, i, sl)
		total += 10;
	assert(tc, total == 0);
	
	// Check iterating over single item list
	list_add(sl, "Randm");
	FOREACH_IN(char*, i, sl)
		total += 10;
	assert(tc, total == 10);
	
	// Check iterating over long list
	list_add(sl, "List_");
	list_add(sl, "_of__");
	list_add(sl, "_some");
	list_add(sl, "five_");
	list_add(sl, "chars");
	list_add(sl, "_long");
	list_add(sl, "texts");
	
	total = 0;
	FOREACH_IN(char*, i, sl)
		total += strlen(i);
	assert(tc, total == 40);
	list_free(sl);
}

void test_list_pop(CuTest* tc) {
	StringList sl = list_new(char, 1);
	list_add(sl, "A1");
	list_add(sl, "A2");
	list_add(sl, "A3");
	assert(tc, 0 == strcmp("A3", list_pop(sl)));
	assert(tc, 0 == strcmp("A2", list_get(sl, 1)));
	assert(tc, 2 == list_len(sl));
	
	list_add(sl, "A5");
	assert(tc, 3 == list_len(sl));
	assert(tc, 0 == strcmp("A2", list_get(sl, 1)));
	assert(tc, 0 == strcmp("A5", list_get(sl, 2)));
}

void test_list_unshift(CuTest* tc) {
	StringList sl = list_new(char, 1);
	list_add(sl, "A1");
	list_add(sl, "A2");
	list_add(sl, "A3");
	assert(tc, 0 == strcmp("A1", list_unshift(sl)));
	assert(tc, 0 == strcmp("A2", list_get(sl, 0)));
	assert(tc, 0 == strcmp("A3", list_get(sl, 1)));
	assert(tc, 2 == list_len(sl));
	
	list_add(sl, "A5");
	assert(tc, 3 == list_len(sl));
	assert(tc, 0 == strcmp("A3", list_get(sl, 1)));
	assert(tc, 0 == strcmp("A5", list_get(sl, 2)));
}

/**
 * Used by test_hashmap_iterator to ensure that every string returned by
 * iterator is one from expected set and occurs only once.
 */
static bool check_and_pull_out(const char* s, char* strings[]) {
	for(size_t i=0; strings[i] != NULL; i++) {
		if (strcmp(s, strings[i]) == 0) {
			strings[i][0] = 0;
			return true;
		}
	}
	return false;
}


void test_hashmap_iterator(CuTest* tc) {
	char* strings[] = { "Ahoj", "Svet", "Hello", "World", NULL };
	map_t map = hashmap_new();
	for(size_t i=0; strings[i] != NULL; i++) {
		hashmap_put(map, strings[i], (void*)1);
		strings[i] = strbuilder_cpy(strings[i]);
		// Copy is needed so check_and_pull_out can modify it
		// to clear already found strings
	}
	
	HashMapIterator i = iter_get(map);
	assert(tc, iter_has_next(i));
	assert(tc, check_and_pull_out(iter_next(i), strings));
	iter_next(i);
	assert(tc, check_and_pull_out(iter_next(i), strings));
	assert(tc, iter_has_next(i));
	assert(tc, check_and_pull_out(iter_next(i), strings));
	assert(tc, !iter_has_next(i));
	
	for(size_t i=0; strings[i] != NULL; i++)
		free(strings[i]);
	iter_free(i);
	hashmap_free(map);
}


/** Fix: Hashmap with single object in it cannot be iterated */
void test_hashmap_iterator_1item(CuTest* tc) {
	map_t map = hashmap_new();
	hashmap_put(map, "single object", (void*)1);
	HashMapIterator i = iter_get(map);
	bool was_inside = false;
	FOREACH(const char*, x, i) {
		// This weird, always true, comparison bellow this is here just
		// to silence warning generated by compiler.
		was_inside = (x != NULL);
	}
	assert(tc, was_inside);
	iter_free(i);
	hashmap_free(map);
}


/** Just test that iteration over 2-items map actually does 2 iterations */
void test_hashmap_iterator_2items(CuTest* tc) {
	map_t map = hashmap_new();
	hashmap_put(map, "1st object", (void*)1);
	hashmap_put(map, "2nd object", (void*)1);
	HashMapIterator i = iter_get(map);
	int times = 0;
	FOREACH(const char*, x, i) {
		times ++;
	}
	assert(tc, times == 2);
	iter_free(i);
	hashmap_free(map);
}


void test_strbuilder(CuTest* tc) {
	// This tests strbuilder_fmt behaviour, as shit it uses work differently on Windows
	char* str;
	str = strbuilder_fmt("a %s b %i", "test", 11);
	assert(tc, strcmp(str, "a test b 11") == 0);
	free(str);
	
	StrBuilder* b = strbuilder_new();
	strbuilder_add(b, "hello");
	strbuilder_add(b, " ");
	strbuilder_add(b, "world");
	assert(tc, strcmp(strbuilder_get_value(b), "hello world") == 0);
	
	strbuilder_add(b, " \n\r");
	strbuilder_rstrip(b, "\n\r rld");
	assert(tc, strcmp(strbuilder_get_value(b), "hello wo") == 0);
	free(strbuilder_consume(b));
	
	b = strbuilder_new();
	strbuilder_add(b, "x");
	strbuilder_add_char(b, '+');
	strbuilder_add(b, "1");
	char* s = strbuilder_consume(b);
	assert(tc, strcmp(s, "x+1") == 0);
	free(s);
	
	b = strbuilder_new();
	strbuilder_add(b, "Piece of ");
	strbuilder_addf(b, "formatted %s with int=%d", "string", 42);
	assert(tc, strcmp(strbuilder_get_value(b), "Piece of formatted string with int=42") == 0);
	free(strbuilder_consume(b));
	
	b = strbuilder_new();
	strbuilder_add(b, "String 'that has' \"to\" be \\escaped");
	strbuilder_escape(b, "'\\\"", '\\');
	assert(tc, strcmp(strbuilder_get_value(b), "String \\'that has\\' \\\"to\\\" be \\\\escaped") == 0);
	
	strbuilder_clear(b);
	strbuilder_add(b, "String that has to be escaped");
	strbuilder_escape(b, "-Ss t", '+');
	assert(tc, strcmp(strbuilder_get_value(b), "+S+tring+ +tha+t+ ha+s+ +to+ be+ e+scaped") == 0);
	
	strbuilder_free(b);
}

void test_strbuilder_escape(CuTest* tc) {
	StrBuilder* b = strbuilder_new();
	strbuilder_add(b, "String 'that has' \"to\" be \\escaped");
	strbuilder_escape(b, "'\\\"", '\\');
	assert(tc, strcmp(strbuilder_get_value(b), "String \\'that has\\' \\\"to\\\" be \\\\escaped") == 0);
	
	strbuilder_clear(b);
	strbuilder_add(b, "String that has to be escaped");
	strbuilder_escape(b, "-Ss t", '+');
	assert(tc, strcmp(strbuilder_get_value(b), "+S+tring+ +tha+t+ ha+s+ +to+ be+ e+scaped") == 0);
	
	strbuilder_clear(b);
	strbuilder_add(b, "String ");
	strbuilder_add_escaped(b, "'that has' \"to\" be \\escaped", "'\\\"", '\\');
	assert(tc, strcmp(strbuilder_get_value(b), "String \\'that has\\' \\\"to\\\" be \\\\escaped") == 0);
	
	strbuilder_clear(b);
	strbuilder_add(b, "String that ");
	strbuilder_add_escaped(b, "has to be escaped", "-Ss t", '+');
	assert(tc, strcmp(strbuilder_get_value(b), "String that ha+s+ +to+ be+ e+scaped") == 0);
	
	// Very special, but real use case
	strbuilder_clear(b);
	strbuilder_add(b, "ls ");
	strbuilder_add(b, "\"");
	strbuilder_add_escaped(b, "hello \"world\"", "\"", '\\');
	strbuilder_add(b, "\"");
	assert(tc, strcmp(strbuilder_get_value(b), "ls \"hello \\\"world\\\"\"") == 0);
	
	strbuilder_free(b);
}

char* template_cb(const char* keyword, int* err_return, void* userdata) {
	if (strcmp(keyword, "world") == 0)
		return "UNIVERSE";
	return "do something with";
}

/** Tests templating function of StrBuilder */
void test_template(CuTest* tc) {
	StrBuilder* b = strbuilder_new();
	strbuilder_add(b, "Hello {world} we are going to {template} this.");
	assert(tc, 1 == strbuilder_template(b, template_cb, NULL, NULL, NULL));
	char* res = strbuilder_consume(b);
	assert(tc, 0 == strcmp("Hello UNIVERSE we are going to do something with this.", res));
	free(res);
	
	b = strbuilder_new();
	strbuilder_add(b, "Brace yourself, this has {no closing brace");
	assert(tc, 1 == strbuilder_template(b, template_cb, NULL, "{}", NULL));
	res = strbuilder_consume(b);
	assert(tc, 0 == strcmp("Brace yourself, this has do something with", res));
	free(res);
}


void test_intmap(CuTest* tc) {
	char* strings[] = { "Ahoj", "Svet", "Hello", "World" };
	intmap_t map = intmap_new();
	
	intmap_put(map, 42, strings[0]);
	intmap_put(map, 15, strings[3]);
	intmap_put(map, 1024, strings[2]);
	intmap_put(map, 9614, strings[3]);
	intmap_put(map, 8815, strings[1]);
	
	any_t r;
	intmap_get(map, 42, &r); assert(tc, 0 == strcmp(r, "Ahoj"));
	intmap_get(map, 9614, &r); assert(tc, 0 == strcmp(r, "World"));
	intmap_get(map, 1024, &r); assert(tc, 0 == strcmp(r, "Hello"));
	
	assert (tc, intmap_get(map, 10, &r) == MAP_MISSING);

	IntMapIterator i = iter_get(map);
	assert(tc, iter_has_next(i));
	intptr_t item = iter_next(i);
	assert(tc, ( (item == 42) || (item == 15) || (item == 1024) || (item == 9614) || (item == 8815) ));
	iter_next(i); iter_next(i); iter_next(i); iter_next(i);	// 4x
	assert(tc, !iter_has_next(i));
	
	iter_free(i);
	intmap_free(map);
}


int main(int argc, char** argv) {
	traceback_set_argv0(argv[0]);
	DEFAULT_SUITE_ADD(test_list);
	DEFAULT_SUITE_ADD(test_list_insert);
	DEFAULT_SUITE_ADD(test_list_filter);
	DEFAULT_SUITE_ADD(test_list_iterator);
	DEFAULT_SUITE_ADD(test_list_for_in);
	DEFAULT_SUITE_ADD(test_list_pop);
	DEFAULT_SUITE_ADD(test_list_unshift);
	DEFAULT_SUITE_ADD(test_intmap);
	DEFAULT_SUITE_ADD(test_hashmap_iterator);
	DEFAULT_SUITE_ADD(test_hashmap_iterator_1item);
	DEFAULT_SUITE_ADD(test_hashmap_iterator_2items);
	DEFAULT_SUITE_ADD(test_strbuilder);
	DEFAULT_SUITE_ADD(test_strbuilder_escape);
	// DEFAULT_SUITE_ADD(test_template);
	
	return CuSuiteRunDefault();
}

