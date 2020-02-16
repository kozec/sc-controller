/**
 * SC-Controller - Math tools
 * 
 * Dequeue, Integer, float and double 2D vectors and some random angle math.
 */
#pragma once
#include <stdbool.h>
#include <stdint.h>
#include <unistd.h>
#include <tgmath.h>

typedef uint64_t monotime_t;

typedef struct {
	int64_t		x;
	int64_t		y;
} ivec_t;

typedef struct {
	float		x;
	float		y;
} fvec_t;

typedef struct {
	double		x;
	double		y;
} dvec_t;

typedef struct {
	dvec_t		*items;
	size_t		size;
	size_t		next;
	size_t		count;
} Dequeue;


#define POW2(x) ( (x) * (x) )
#define fvec_len(v) sqrtf(POW2(v.x) + POW2(v.y))
#define dvec_len(v) sqrt(POW2(v.x) + POW2(v.y))
#define vec_set(dst, vx, vy) do { (dst).x = (vx); (dst).y = (vy); } while(0);
#define vec_cpy(dst, src) do { (dst).x = (src).x; (dst).y = (src).y; } while(0);
#define vec_mul(v, v2) do { (v).x *= (v2).x; (v).y *= (v2).y; } while(0);
#define vec_muls(v, scalar) do { (v).x *= (scalar); (v).y *= (scalar); } while(0);

#ifndef min
#define min(x, y) ( ((x)<(y)) ? (x) : (y) )
#endif
#ifndef max
#define max(x, y) ( ((x)>(y)) ? (x) : (y) )
#endif
#define clamp(x, v, y) ( ((v)<(x)) ? (x) : ( ((v)>(y)) ? (y) : (v) ) )

#ifndef M_PI
#define M_PI		3.14159265358979323846
#endif


/**
 * Initializes (and clears) dequeue.
 * Should allocation fail, dq->items will be set to NULL and method returns false
 */
bool dequeue_init(Dequeue* dq, size_t size);

/** Clears the dequeue */
void dequeue_clear(Dequeue* dq);

/** Adds values to dequeue, removing oldest added value if necessary */
void dequeue_add(Dequeue* dq, double x, double y);

/** Sets average of all values in dequeue to 'x' and 'y' */
void dequeue_avg(Dequeue* dq, double* x, double* y);

#define dequeue_len(dq) ((dq)->size)
/** Frees memory allocated by dequeue_init */
#define dequeue_deinit(dq) free((dq)->items)

/**
 * Converts quaternion to pitch, yaw and roll
 * and stores computed values (-PI to PI range) in 'pyr'
 */
void quat2euler(double pyr[3], double q0, double q1, double q2, double q3);

/* Returns shorter distance between two angles. 'a1' and 'a2' are in radians */
double anglediff(double a1, double a2);

/* Projects (in place) coordinate in circle (of radius 1.0) to coordinate in square. */
void circle_to_square(double* x, double* y);

/** Returns current value of CLOCK_MONOTONIC converted to number of milliseconds */
monotime_t mono_time_ms();

/** As mono_time_ms, but returns number of seconds as double */
double mono_time_d();

