#define _hypot hypot
#include <Python.h>
#include <structmember.h>
#include "mingw.thread.h"
#ifndef _In_
#define _In_
#define _Out_
#endif
// Note: Following includes cpp source
#include "ViGEm/ViGEmClient.cpp"

extern "C" {

static PVIGEM_CLIENT client;
static PyObject* module;


struct vigemclient_xusb_report {
	PyObject_HEAD
	XUSB_REPORT report;
};


static PyMemberDef vigemclient_xusb_report_members[] = {
	{ (char*)"wButtons", T_USHORT, offsetof(struct vigemclient_xusb_report, report.wButtons), 0, NULL },
	{ (char*)"bLeftTrigger", T_BYTE, offsetof(struct vigemclient_xusb_report, report.bLeftTrigger), 0, NULL },
	{ (char*)"bRightTrigger", T_BYTE, offsetof(struct vigemclient_xusb_report, report.bRightTrigger), 0, NULL}, 
	{ (char*)"sThumbLX", T_SHORT, offsetof(struct vigemclient_xusb_report, report.sThumbLX), 0, NULL },
	{ (char*)"sThumbLY", T_SHORT, offsetof(struct vigemclient_xusb_report, report.sThumbLY), 0, NULL },
	{ (char*)"sThumbRX", T_SHORT, offsetof(struct vigemclient_xusb_report, report.sThumbRX), 0, NULL },
	{ (char*)"sThumbRY", T_SHORT, offsetof(struct vigemclient_xusb_report, report.sThumbRY), 0, NULL },
	{NULL}
};


static void vigemclient_xusb_dealloc(PyObject* self) {
	PyObject_Del(self);
}


static PyTypeObject vigemclient_xusb_report_Type = {
	PyObject_HEAD_INIT(&PyType_Type)
	0,												// ob_size
	"XUSBReport",									// tp_name
	(int)sizeof(struct vigemclient_xusb_report),	// tp_basicsize
	0,												// tp_itemsize
	vigemclient_xusb_dealloc,						// tp_dealloc
};


/**
 * Sets exception and string and returns NULL for error code passed in argument
 * or returns None if there is no error.
 */
static PyObject* _raise_if_vigem_error(VIGEM_ERROR err) {
	switch (err) {
		case VIGEM_ERROR_NONE:
			Py_RETURN_NONE;
		case VIGEM_ERROR_BUS_NOT_FOUND:
			PyErr_SetString(PyExc_OSError, "VIGEM_ERROR_BUS_NOT_FOUND");
		case VIGEM_ERROR_NO_FREE_SLOT:
			PyErr_SetString(PyExc_OSError, "VIGEM_ERROR_NO_FREE_SLOT");
		case VIGEM_ERROR_INVALID_TARGET:
			PyErr_SetString(PyExc_OSError, "VIGEM_ERROR_INVALID_TARGET");
		case VIGEM_ERROR_REMOVAL_FAILED:
			PyErr_SetString(PyExc_OSError, "VIGEM_ERROR_REMOVAL_FAILED");
		case VIGEM_ERROR_ALREADY_CONNECTED:
			PyErr_SetString(PyExc_OSError, "VIGEM_ERROR_ALREADY_CONNECTED");
		case VIGEM_ERROR_TARGET_UNINITIALIZED:
			PyErr_SetString(PyExc_OSError, "VIGEM_ERROR_TARGET_UNINITIALIZED");
		case VIGEM_ERROR_TARGET_NOT_PLUGGED_IN:
			PyErr_SetString(PyExc_OSError, "VIGEM_ERROR_TARGET_NOT_PLUGGED_IN");
		case VIGEM_ERROR_BUS_VERSION_MISMATCH:
			PyErr_SetString(PyExc_OSError, "VIGEM_ERROR_BUS_VERSION_MISMATCH");
		case VIGEM_ERROR_BUS_ACCESS_FAILED:
			PyErr_SetString(PyExc_OSError, "VIGEM_ERROR_BUS_ACCESS_FAILED");
		case VIGEM_ERROR_CALLBACK_ALREADY_REGISTERED:
			PyErr_SetString(PyExc_OSError, "VIGEM_ERROR_CALLBACK_ALREADY_REGISTERED");
		case VIGEM_ERROR_CALLBACK_NOT_FOUND:
			PyErr_SetString(PyExc_OSError, "VIGEM_ERROR_CALLBACK_NOT_FOUND");
		case VIGEM_ERROR_BUS_ALREADY_CONNECTED:
			PyErr_SetString(PyExc_OSError, "VIGEM_ERROR_BUS_ALREADY_CONNECTED");
		default:
			PyErr_SetString(PyExc_OSError, "Unknown VIGEM_ERROR");
	}
	return NULL;
}


static PyObject* vigemclient_connect(PyObject* self, PyObject* args) {
	return _raise_if_vigem_error(vigem_connect(client));
}


static PyObject* vigemclient_disconnect(PyObject* self, PyObject* args) {
	vigem_disconnect(client);
	Py_RETURN_NONE;
}


static void vigemclient_target_desctructor(PyObject* capsule) {
	PVIGEM_TARGET target = (PVIGEM_TARGET)PyCapsule_GetPointer(capsule, "PVIGEM_TARGET");
	if (target != NULL)
		vigem_target_free(target);
}


static PyObject* vigemclient_target_x360_alloc(PyObject* self, PyObject* args) {
	PVIGEM_TARGET target = vigem_target_x360_alloc();
	if (target != NULL)
		return PyCapsule_New(target, "PVIGEM_TARGET", vigemclient_target_desctructor);
	PyErr_SetString(PyExc_MemoryError, "Allocation failed");
	return NULL;
}


static PyObject* vigemclient_target_add(PyObject* self, PyObject* capsule) {
	PVIGEM_TARGET target = (PVIGEM_TARGET)PyCapsule_GetPointer(capsule, "PVIGEM_TARGET");
	if (target == NULL) return NULL;		// exception set by PyCapsule_GetPointer
	VIGEM_ERROR err = vigem_target_add(client, target);
	if (err == VIGEM_ERROR_NONE)
		Py_INCREF(capsule);
	return _raise_if_vigem_error(err);
}


static PyObject* vigemclient_target_remove(PyObject* self, PyObject* capsule) {
	PVIGEM_TARGET target = (PVIGEM_TARGET)PyCapsule_GetPointer(capsule, "PVIGEM_TARGET");
	if (target == NULL) return NULL;		// exception set by PyCapsule_GetPointer
	VIGEM_ERROR err = vigem_target_remove(client, target);
	if (err == VIGEM_ERROR_NONE)
		Py_DECREF(capsule);
	return _raise_if_vigem_error(err);
}


static PyObject* vigemclient_target_is_attached(PyObject* self, PyObject* capsule) {
	PVIGEM_TARGET target = (PVIGEM_TARGET)PyCapsule_GetPointer(capsule, "PVIGEM_TARGET");
	if (target == NULL) return NULL;		// exception set by PyCapsule_GetPointer
	if (vigem_target_is_attached(target)) {
		Py_RETURN_TRUE;
	} else {
		Py_RETURN_FALSE;
	}
}


static PyObject* vigemclient_target_x360_update(PyObject* self, PyObject* args) {
	PyObject* capsule;
	PyObject* report;
	if (!PyArg_ParseTuple(args, "OO", &capsule, &report))
		return NULL;						// exception set by PyArg_ParseTuple
	PVIGEM_TARGET target = (PVIGEM_TARGET)PyCapsule_GetPointer(capsule, "PVIGEM_TARGET");
	if (target == NULL) return NULL;		// exception set by PyCapsule_GetPointer

	if (!PyObject_TypeCheck(report, &vigemclient_xusb_report_Type)) {
		PyErr_SetString(PyExc_TypeError, "Argument is not XUSBReport instance");
		return NULL;
	}
	
	
	VIGEM_ERROR err = vigem_target_x360_update(client, target, ((struct vigemclient_xusb_report*)report)->report);
	return _raise_if_vigem_error(err);
}


/*static void vigemclient_xusb_desctructor(PyObject* capsule) {
	PVIGEM_TARGET target = (PVIGEM_TARGET)PyCapsule_GetPointer(capsule, "XUSB_REPORT");
	if (target != NULL)
		free(target);
}


static PyObject* vigemclient_xusb_alloc(PyObject* self, PyObject* args) {
	XUSB_REPORT* report = (XUSB_REPORT*)malloc(sizeof(XUSB_REPORT));
	if (report != NULL)
		return PyCapsule_New(report, "XUSB_REPORT", vigemclient_xusb_desctructor);
	PyErr_SetString(PyExc_MemoryError, "Allocation failed");
	return NULL;
}


static PyObject* vigemclient_xusb_set_buttons(PyObject* self, PyObject* args) {
	PyObject* capsule;
	long int buttons;
	if (!PyArg_ParseTuple(args, "Ol", &capsule, &buttons))
		return NULL;						// exception set by PyArg_ParseTuple
	XUSB_REPORT* report = (XUSB_REPORT*)PyCapsule_GetPointer(capsule, "XUSB_REPORT");
	if (report == NULL) return NULL;		// exception set by PyCapsule_GetPointer
	
	report->wButtons = buttons;
	Py_RETURN_NONE;
}*/


static PyObject* vigemclient_xusb_alloc(PyObject* self, PyObject* args) {
	return (PyObject*)PyObject_NEW(struct vigemclient_xusb_report, &vigemclient_xusb_report_Type);
}



static PyMethodDef methods[] = {
	{ "disconnect", vigemclient_disconnect, METH_NOARGS, "Disconnects from the bus device and resets the driver object state" },
	{ "connect", vigemclient_connect, METH_NOARGS, "Initializes the driver object and establishes a connection to the emulation bus driver" },
	
	{ "target_x360_alloc", vigemclient_target_x360_alloc, METH_NOARGS, "Allocates an object representing an Xbox 360 Controller device" },
	{ "target_add", vigemclient_target_add, METH_O, "Adds a provided target device to the bus driver, which is equal to a device plug-in event of a physical hardware device" },
	{ "target_remove", vigemclient_target_remove, METH_O, "Removes a provided target device from the bus driver, which is equal to a device unplug event of a physical hardware device" },
	{ "target_is_attached", vigemclient_target_is_attached, METH_O, "Returns True if the provided target device object is currently attached to the bus" },
	{ "target_x360_update", vigemclient_target_x360_update, METH_VARARGS, "Sends a state report to the provided target device" },
	
	{ "XUSBReport", vigemclient_xusb_alloc, METH_NOARGS, "Creates new XINPUT_GAMEPAD-compatible report instance" },
	
	// { "xusb_alloc", vigemclient_xusb_alloc, METH_NOARGS, "Creates new XINPUT_GAMEPAD-compatible report instance" },
	// { "xusb_set_buttons", vigemclient_xusb_set_buttons, METH_VARARGS, "Creates new XINPUT_GAMEPAD-compatible report instance" },
	{ NULL, NULL, 0, NULL }
};


PyMODINIT_FUNC initvigemclient(void) {
	vigemclient_xusb_report_Type.tp_flags = Py_TPFLAGS_HAVE_CLASS;
	vigemclient_xusb_report_Type.tp_members = vigemclient_xusb_report_members;
	
	client = vigem_alloc();
	if (client != NULL)
		module = Py_InitModule("vigemclient", methods);
}

}