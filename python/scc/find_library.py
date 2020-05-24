#!/usr/bin/env python2
"""
SC-Controller - find_library

This method is imported on multiple places and was causing circular import hell
"""
import os, sys, ctypes, imp, platform

_find_library_cache = {}


def find_library(libname):
	"""
	Search for 'libname.so'.
	Returns library loaded with ctypes.CDLL
	Raises OSError if library is not found
	"""
	if libname in _find_library_cache:
		return _find_library_cache[libname]
	
	base_path = os.path.dirname(__file__)
	lib, search_paths = None, []
	so_extensions = [ ext for ext, _, typ in imp.get_suffixes()
			if typ == imp.C_EXTENSION ]
	if platform.system() == "Windows":
		so_extensions.append(".dll")
	for extension in so_extensions:
		if platform.system() == "Windows":
			search_paths += [
				os.path.abspath(os.path.normpath("./" + libname + extension))
			]
		search_paths += [
			os.path.abspath(os.path.normpath(
				os.path.join( './', libname + extension ))),
			os.path.abspath(os.path.normpath(
				os.path.join( base_path, '..', libname + extension ))),
			os.path.abspath(os.path.normpath(
				os.path.join( base_path, '../..', libname + extension ))),
			os.path.abspath(os.path.normpath(
				os.path.join( './build', libname + extension ))),
			]
		if os.environ.get('LD_LIBRARY_PATH'):
			search_paths.append(os.path.abspath(os.path.normpath(
				os.path.join( os.environ['LD_LIBRARY_PATH'], libname + extension )))),
	for path in search_paths:
		if os.path.exists(path):
			lib = path
			break
	
	if not lib:
		raise OSError('Cant find %s.so. searched at:\n %s' % (
			libname, '\n'.join(search_paths)))
	cdll = ctypes.CDLL(lib)
	_find_library_cache[libname] = cdll
	return cdll

