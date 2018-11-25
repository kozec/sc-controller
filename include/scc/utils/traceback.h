/**
 * Wrapper over 'backtrace' and 'addr2line'. This is very-much hacked together
 * and used only for debugging. It makes assumptions on outputs, prints colorful
 * text and depends on linux-only stuff, but can be completly disabled by
 * defining NO_TRACEBACKS.
 *
 * Also, this is totally NOT thread-safe.
 */

#pragma once

#define MAX_TRACEBACK_SIZE 32

/** Initializes traceback code */
void traceback_set_argv0(const char* executablename);

/**
 * Outputs traceback up to current position.
 * 'skip' determines how many most-recent calls should be skipped,
 * 1 being usual value to skip just 'traceback_print' call.
 */
void traceback_print(int skip);

/** Prints "Traceback (most recent last):" */
void traceback_print_header();
