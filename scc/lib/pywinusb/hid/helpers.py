# -*- coding: utf-8 -*-

"""Helper classs, functions and decorators"""
from __future__ import absolute_import
from __future__ import print_function

import sys
if sys.version_info >= (3,):
    from collections import UserList  # pylint: disable=no-name-in-module
else:
    # python 2
    from UserList import UserList  # pylint: disable=import-error

class HIDError(Exception):
    "Main HID error exception class type"
    pass

def simple_decorator(decorator):
    """This decorator can be used to turn simple functions
    into well-behaved decorators, so long as the decorators
    are fairly simple. If a decorator expects a function and
    returns a function (no descriptors), and if it doesn't
    modify function attributes or docstring, then it is
    eligible to use this. Simply apply @simple_decorator to
    your decorator and it will automatically preserve the
    docstring and function attributes of functions to which
    it is applied."""
    def new_decorator(funct_target):
        """This will be modified"""
        decorated = decorator(funct_target)
        decorated.__name__ = funct_target.__name__
        decorated.__doc__  = funct_target.__doc__
        decorated.__dict__.update(funct_target.__dict__)
        return decorated
    # Now a few lines needed to make simple_decorator itself
    # be a well-behaved decorator.
    new_decorator.__name__ = decorator.__name__
    new_decorator.__doc__ = decorator.__doc__
    new_decorator.__dict__.update(decorator.__dict__)
    return new_decorator

#
# Sample Use:
#
@simple_decorator
def logging_decorator(func):
    """Allow logging function calls"""
    def you_will_never_see_this_name(*args, **kwargs):
        """Neither this docstring"""
        print('calling %s ...' % func.__name__)
        result = func(*args, **kwargs)
        print('completed: %s' % func.__name__)
        return result
    return you_will_never_see_this_name

def synchronized(lock):
    """ Synchronization decorator.
    Allos to set a mutex on any function
    """
    @simple_decorator
    def wrap(function_target):
        """Decorator wrapper"""
        def new_function(*args, **kw):
            """Decorated function with Mutex"""
            lock.acquire()
            try:
                return function_target(*args, **kw)
            finally:
                lock.release()
        return new_function
    return wrap

class ReadOnlyList(UserList):
    "Read only sequence wrapper"
    def __init__(self, any_list):
        UserList.__init__(self, any_list)
    def __setitem__(self, index, value):
        raise ValueError("Object is read-only")

