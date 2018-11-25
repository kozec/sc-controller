#define _POSIX_C_SOURCE 200809L
#include "scc/utils/traceback.h"
#include "scc/utils/logging.h"
#include "scc/utils/math.h"
#include <time.h>
#include <math.h>

bool dequeue_init(Dequeue* dq, size_t size) {
	dq->size = size;
	dq->next = dq->count = 0;
	dq->items = malloc(sizeof(dq->items[0]) * size);
	return (dq->items != NULL);
}

void dequeue_clear(Dequeue* dq) {
	dq->next = dq->count = 0;
}

void dequeue_add(Dequeue* dq, double x, double y) {
	dq->items[dq->next].x = x;
	dq->items[dq->next].y = y;
	dq->next ++;
	if (dq->next >= dq->size)
		dq->next = 0;
	if (dq->next > dq->count)
		dq->count = dq->next;
}

void dequeue_avg(Dequeue* dq, double* x, double* y) {
	*x = *y = 0;
	for (size_t i=0; i<dq->count; i++) {
		*x += dq->items[i].x;
		*y += dq->items[i].y;
	}
	
	*x /= (double)dq->count;
	*y /= (double)dq->count;
}

uint64_t mono_time_ms() {
	static struct timespec t;
	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec * 1000 + (t.tv_nsec / 10e6);
}

double mono_time_d() {
	static struct timespec t;
	clock_gettime(CLOCK_MONOTONIC, &t);
	return (double)t.tv_sec + ((double)t.tv_nsec / (double)10e8);
}
