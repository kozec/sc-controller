/**
 * Glue between code from future and current stuff in python
 */
#pragma once
#include "Python.h"
#include <stdbool.h>
#include <stdint.h>

#define LERROR(fmt, ...) do { fprintf(stderr, "E " LOG_TAG " " fmt, ##__VA_ARGS__); fprintf(stderr, "\n"); fflush(stderr); } while(0)
#define WARN(fmt, ...) do { fprintf(stderr, "W " LOG_TAG " " fmt, ##__VA_ARGS__); fprintf(stderr, "\n"); fflush(stderr); } while(0)
#define DEBUG(fmt, ...) do { fprintf(stdout, "D " LOG_TAG " " fmt, ##__VA_ARGS__); fprintf(stdout, "\n"); fflush(stdout); } while(0)
#define LOG(fmt, ...) do { fprintf(stdout, "L " LOG_TAG " " fmt, ##__VA_ARGS__); fprintf(stdout, "\n"); fflush(stdout); } while(0)

typedef uint64_t monotime_t;

/** Returns current value of CLOCK_MONOTONIC converted to number of milliseconds */
inline static uint64_t mono_time_ms() {
	static struct timespec t;
	clock_gettime(CLOCK_MONOTONIC, &t);
	return t.tv_sec * 1000 + (t.tv_nsec / 10e5);
}

