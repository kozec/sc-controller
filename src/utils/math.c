#define _POSIX_C_SOURCE 200809L
#include "scc/utils/traceback.h"
#include "scc/utils/logging.h"
#include "scc/utils/math.h"
#include <math.h>
#include <time.h>
#define M_PId4 (M_PI / 4.0)

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

void quat2euler(double pyr[3], double q0, double q1, double q2, double q3) {
	double qq0 = q0 * q0;
	double qq1 = q1 * q1;
	double qq2 = q2 * q2;
	double qq3 = q3 * q3;
	double xa = qq0 - qq1 - qq2 + qq3;
	double xb = 2 * (q0 * q1 + q2 * q3);
	double xn = 2 * (q0 * q2 - q1 * q3);
	double yn = 2 * (q1 * q2 + q0 * q3);
	double zn = qq3 + qq2 - qq0 - qq1;
	
	pyr[0] = atan2(xb , xa);
	pyr[1] = atan2(xn , sqrt(1 - xn*xn));
	pyr[2] = atan2(yn , zn);
}


double anglediff(double a1, double a2) {
	return fmod((a2 - a1 + M_PI), (2.0 * M_PI) - M_PI);
}

void circle_to_square(double* x, double* y) {
	// Adapted from http://theinstructionlimit.com/squaring-the-thumbsticks
	
	// Determine the theta angle
	double angle = atan2(*y, *x) + M_PI;
	
	// Scale according to which wall we're clamping to
	if ((angle <= M_PId4) || (angle > 7.0 * M_PId4)) {
		// X+ wall
		*x = *x * (1.0 / cos(angle));
		*y = *y * (1.0 / cos(angle));
	} else if ((angle > M_PId4) && (angle <= 3.0 * M_PId4)) {
		// Y+ wall
		*x = *x * (1.0 / sin(angle));
		*y = *y * (1.0 / sin(angle));
	} else if ((angle > 3.0 * M_PId4) && (angle <= 5.0 * M_PId4)) {
		// X- wall
		*x = *x * (-1.0 / cos(angle));
		*y = *y * (-1.0 / cos(angle));
	} else if ((angle > 5.0 * M_PId4) && (angle <= 7.0 * M_PId4)) {
		// Y- wall
		*x = *x * (-1.0 / sin(angle));
		*y = *y * (-1.0 / sin(angle));
	} else {
		LERROR("circle_to_square: invalid input");
		*x = 0;
		*y = 0;
	}
}

uint64_t mono_time_ms() {
	static struct timespec t;
	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec * 1000 + (t.tv_nsec / 10e5);
}

double mono_time_d() {
	static struct timespec t;
	clock_gettime(CLOCK_MONOTONIC, &t);
	return (double)t.tv_sec + ((double)t.tv_nsec / (double)10e8);
}

