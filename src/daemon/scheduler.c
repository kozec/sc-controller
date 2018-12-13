/**
 * SC-Controller - Daemon - Scheduler
 *
 * Keeps list of callbacks ordered by time when they are to be executed,
 * executes them when time is ripe.
 */

#define LOG_TAG "Scheduler"
#include "scc/utils/logging.h"
#include "scc/utils/iterable.h"
#include "scc/utils/assert.h"
#include "scc/utils/list.h"
#include "scc/utils/math.h"
#include "daemon.h"
#include <sys/time.h>
#include <errno.h>

// TODO: Use epoll_wait instead of select

typedef struct Task {
	/** at is value of 'now' (in ms) when task will be executed */
	monotime_t						at;
	sccd_scheduler_cb_internal		callback;
	void*							userdata;
	/**
	 * parent is another form of userdata, used when removing tasks
	 * by mapper and to match 'MapperScheduleCallback' signature
	 */
	void*							parent;
} Task;

typedef LIST_TYPE(Task) TaskList;

static monotime_t now;			// 'now' is monotonic time in ms
static TaskList tasks;

static void sccd_scheduler_mainloop(Daemon* d) {
	now = mono_time_ms();
	if (list_len(tasks)) {
		Task* task = list_get(tasks, 0);
		if (task->at <= now) {
			// TODO: list_unshift would be nice
			list_remove(tasks, task);
			task->callback(task->parent, task->userdata);
			free(task);
		}
	}
}

void sccd_scheduler_init() {
	Daemon* d = get_daemon();
	tasks = list_new(Task, 32);
	ASSERT(tasks != NULL);
	ASSERT(d->mainloop_cb_add(&sccd_scheduler_mainloop));
	now = mono_time_ms();
}

void sccd_scheduler_close() {
	// nothing
	list_foreach(tasks, &free);
	list_free(tasks);
}

void sccd_scheduler_get_sleep_time(struct timeval* t) {
	t->tv_sec = 0;
	t->tv_usec = MIN_SLEEP_TIME * 1000;
	if (list_len(tasks) > 0) {
		Task* task = list_get(tasks, 0);
		if (task->at <= now) {
			// This should already been executed
			t->tv_usec = 0;
			return;
		}
		if ((task->at - now) < t->tv_usec)
			t->tv_usec = task->at - now;
	}
}

TaskID sccd_scheduler_schedule(uint32_t timeout, sccd_scheduler_cb_internal cb, void* parent, void* userdata) {
	monotime_t at = now + (monotime_t)timeout;
	if (!list_allocate(tasks, 1))
		return (TaskID)NULL;	// oom
	Task* task = malloc(sizeof(Task));
	if (task == NULL)
		return (TaskID)NULL;	// oom
	
	task->at = at;
	task->callback = cb;
	task->parent = parent;
	task->userdata = userdata;
	
	// It's important to keep callbacks in order as they will be executed
	for(int i=0; i<list_len(tasks); i++) {
		if (at < tasks->items[i]->at) {
			list_insert(tasks, i, task);
			return (TaskID)task;
		}
	}
	list_add(tasks, task);
	return (TaskID)task;
}

void* sccd_scheduler_get_user_data(TaskID id) {
	FOREACH_IN(Task*, task, tasks)
		if (task == (Task*)id)
			return task->userdata;
	return NULL;
}

void sccd_scheduler_cancel(TaskID id) {
	FOREACH_IN(Task*, task, tasks) {
		if (task == (Task*)id) {
			list_remove(tasks, task);
			free(task);
			return;
		}
	}
}
