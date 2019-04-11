#pragma once
#ifdef __cplusplus
extern "C" {
#endif

#ifndef DLL_EXPORT

#ifdef __MINGW32__
#		define DLL_EXPORT __attribute__((visibility("default")))
#elif defined _WIN32 || defined __CYGWIN__
#	define DLL_EXPORT __declspec(dllexport)
#else
#	if __GNUC__ >= 4
#		define DLL_EXPORT __attribute__((visibility("default")))
#	else
#		define DLL_EXPORT
#	endif
#endif
#endif

#ifdef __cplusplus
}
#endif

