#!/usr/bin/env python2
"""
SC-Controller - Scheduler

Centralized scheduler that should be used everywhere.
Runs in SCCDaemon's (single-threaded) mainloop. That means all callbacks are
also called on main thread.

Use schedule(delay, callback, *data) to register one-time task.
"""
import time, Queue, logging
log = logging.getLogger("Scheduler")

# TODO: Maybe create actual thread for this? Use poler? Scrap everything and rewrite it in GO?

class Scheduler(object):
	
	def __init__(self):
		self._scheduled = Queue.PriorityQueue()
		self._next = None
		self._now = time.time()
	
	
	def schedule(self, delay, callback, *data):
		"""
		Schedules one-time task to be executed no sooner than after 'delay' of
		secounds. Delay may be float number.
		'callback' is called as callback(*data).
		
		Returned Task instance can be used to cancel task once scheduled.
		"""
		task = Task(self._now + delay, callback, data)
		if self._next is None or task.time < self._next.time:
			if self._next:
				self._scheduled.put(self._next)
			self._next = task
		else:
			self._scheduled.put(task)
		return task
	
	
	def cancel_task(self, task):
		"""
		Returns True if task was sucessfully removed or False if task was
		already executed or not known at all.
		
		Note that this is slow as hell and completly thread-unsafe,
		so it _has_ to be called on main thread.
		"""
		print "cancel", task
		if task == self._next:
			self._next = None if self._scheduled.empty() else self._scheduled.get()
			print "canceled", task
			return True
		# Fun part: All tasks are removed from PriorityQueue
		# until correct is found. Then everything is put back
		tasks, found = [], False
		while not self._scheduled.empty():
			t = self._scheduled.get()
			if t == task:
				found = True
				break
			tasks.append(t)
		for t in tasks:
			self._scheduled.put(t)
		if found:
			print "canceled", task
		return found
	
	
	def run(self):
		self._now = time.time()
		while self._next and self._now >= self._next.time:
			callback, data = self._next.callback, self._next.data
			self._next = None if self._scheduled.empty() else self._scheduled.get()
			callback(*data)


class Task(object):
	
	def __init__(self, time, callback, data):
		self.time = time
		self.callback = callback
		self.data = data
