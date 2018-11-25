#include <assert.h>
#include <setjmp.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <math.h>

#include "CuTest.h"

/*-------------------------------------------------------------------------*
 * CuTest
 *-------------------------------------------------------------------------*/

void CuTestInit(CuTest* t, const char* name, TestFunction function)
{
	t->name = strbuilder_cpy(name);
	t->failed = 0;
	t->ran = 0;
	t->message = NULL;
	t->function = function;
	t->jumpBuf = NULL;
}

CuTest* CuTestNew(const char* name, TestFunction function)
{
	CuTest* tc = CU_ALLOC(CuTest);
	CuTestInit(tc, name, function);
	return tc;
}

void CuTestDelete(CuTest *t)
{
        if (!t) return;
        free(t->name);
        free(t);
}

void CuTestRun(CuTest* tc)
{
	jmp_buf buf;
	tc->jumpBuf = &buf;
	if (setjmp(buf) == 0)
	{
		tc->ran = 1;
		(tc->function)(tc);
	}
	tc->jumpBuf = 0;
}

static void CuFailInternal(CuTest* tc, const char* file, int line, StrBuilder* sb)
{
	strbuilder_insertf(sb, 0, "%s:%d: ", file, line);

	tc->failed = 1;
	tc->message = strbuilder_consume(sb);
	if (tc->jumpBuf != 0) longjmp(*(tc->jumpBuf), 0);
}

void CuFail_Line(CuTest* tc, const char* file, int line, const char* message2, const char* message)
{
	StrBuilder* sb = strbuilder_new(STRING_MAX);
	if (message2 != NULL) 
	{
		strbuilder_add(sb, message2);
		strbuilder_add(sb, ": ");
	}
	strbuilder_add(sb, message);
	CuFailInternal(tc, file, line, sb);
}

void CuAssert_Line(CuTest* tc, const char* file, int line, const char* message, int condition)
{
	if (condition) return;
	CuFail_Line(tc, file, line, NULL, message);
}

void CuAssertStrEquals_LineMsg(CuTest* tc, const char* file, int line, const char* message, 
	const char* expected, const char* actual)
{
	if ((expected == NULL && actual == NULL) ||
		(expected != NULL && actual != NULL &&
		strcmp(expected, actual) == 0))
	{
		return;
	}

	StrBuilder* sb = strbuilder_new(STRING_MAX);
	if (message != NULL) 
	{
		strbuilder_add(sb, message);
		strbuilder_add(sb, ": ");
	}
	strbuilder_add(sb, "expected <");
	strbuilder_add(sb, expected);
	strbuilder_add(sb, "> but was <");
	strbuilder_add(sb, actual);
	strbuilder_add(sb, ">");
	CuFailInternal(tc, file, line, sb);
}

void CuAssertIntEquals_LineMsg(CuTest* tc, const char* file, int line, const char* message, 
	int expected, int actual)
{
	char buf[STRING_MAX];
	if (expected == actual) return;
	sprintf(buf, "expected <%d> but was <%d>", expected, actual);
	CuFail_Line(tc, file, line, message, buf);
}

void CuAssertDblEquals_LineMsg(CuTest* tc, const char* file, int line, const char* message, 
	double expected, double actual, double delta)
{
	char buf[STRING_MAX];
	if (fabs(expected - actual) <= delta) return;
	sprintf(buf, "expected <%f> but was <%f>", expected, actual); 

	CuFail_Line(tc, file, line, message, buf);
}

void CuAssertPtrEquals_LineMsg(CuTest* tc, const char* file, int line, const char* message, 
	void* expected, void* actual)
{
	char buf[STRING_MAX];
	if (expected == actual) return;
	sprintf(buf, "expected pointer <0x%p> but was <0x%p>", expected, actual);
	CuFail_Line(tc, file, line, message, buf);
}


/*-------------------------------------------------------------------------*
 * CuSuite
 *-------------------------------------------------------------------------*/

void CuSuiteInit(CuSuite* testSuite)
{
	testSuite->count = 0;
	testSuite->failCount = 0;
        memset(testSuite->list, 0, sizeof(testSuite->list));
}

CuSuite* CuSuiteNew(void)
{
	CuSuite* testSuite = CU_ALLOC(CuSuite);
	CuSuiteInit(testSuite);
	return testSuite;
}

void CuSuiteDelete(CuSuite *testSuite)
{
        unsigned int n;
        for (n=0; n < MAX_TEST_CASES; n++)
        {
                if (testSuite->list[n])
                {
                        CuTestDelete(testSuite->list[n]);
                }
        }
        free(testSuite);

}

void CuSuiteAdd(CuSuite* testSuite, CuTest *testCase)
{
	// assert(testSuite->count < MAX_TEST_CASES);
	if (testSuite->count >= MAX_TEST_CASES) {
		fprintf(stderr, "Test count overflow\n");
		exit(1);
	}
	testSuite->list[testSuite->count] = testCase;
	testSuite->count++;
}

void CuSuiteAddSuite(CuSuite* testSuite, CuSuite* testSuite2)
{
	int i;
	for (i = 0 ; i < testSuite2->count ; ++i)
	{
		CuTest* testCase = testSuite2->list[i];
		CuSuiteAdd(testSuite, testCase);
	}
}

void CuSuiteRun(CuSuite* testSuite)
{
	int i;
	for (i = 0 ; i < testSuite->count ; ++i)
	{
		CuTest* testCase = testSuite->list[i];
		CuTestRun(testCase);
		if (testCase->failed) { testSuite->failCount += 1; }
	}
}

void CuSuiteSummary(CuSuite* testSuite, StrBuilder* summary)
{
	int i;
	for (i = 0 ; i < testSuite->count ; ++i)
	{
		CuTest* testCase = testSuite->list[i];
		strbuilder_add(summary, testCase->failed ? "F" : ".");
	}
	strbuilder_add(summary, "\n\n");
}

int CuSuiteDetails(CuSuite* testSuite, StrBuilder* details)
{
	int i;
	int failCount = 0;

	if (testSuite->failCount == 0)
	{
		int passCount = testSuite->count - testSuite->failCount;
		const char* testWord = passCount == 1 ? "test" : "tests";
		strbuilder_addf(details, "OK (%d %s)\n", passCount, testWord);
	}
	else
	{
		if (testSuite->failCount == 1)
			strbuilder_add(details, "There was 1 failure:\n");
		else
			strbuilder_addf(details, "There were %d failures:\n", testSuite->failCount);

		for (i = 0 ; i < testSuite->count ; ++i)
		{
			CuTest* testCase = testSuite->list[i];
			if (testCase->failed)
			{
				failCount++;
				strbuilder_addf(details, "%d) %s: %s\n",
					failCount, testCase->name, testCase->message);
			}
		}
		strbuilder_add(details, "\n!!!FAILURES!!!\n");

		strbuilder_addf(details, "Runs: %d ",   testSuite->count);
		strbuilder_addf(details, "Passes: %d ", testSuite->count - testSuite->failCount);
		strbuilder_addf(details, "Fails: %d\n",  testSuite->failCount);
	}
	return failCount;
}


/*-------------------------------------------------------------------------*
 * Default suite
 *-------------------------------------------------------------------------*/

CuSuite* default_suite = NULL;


CuSuite* CuSuiteGetDefault() {
	if (default_suite == NULL) {
		default_suite = CuSuiteNew();
	}
	return default_suite;
}


int CuSuiteRunDefault() {
	CuSuiteRun(DEFAULT_SUITE);
	StrBuilder* output = strbuilder_new(1024);
	CuSuiteSummary(DEFAULT_SUITE, output);
	int failCount = CuSuiteDetails(DEFAULT_SUITE, output);
	if (failCount == 0) {
		printf("%s\n", strbuilder_get_value(output));
		strbuilder_free(output);
		return 0;
	} else {
		fprintf(stderr, "%s\n", strbuilder_get_value(output));
		strbuilder_free(output);
		return 1;
	}
}
