/**
 * SC Controller - Input Device - wrapper for DirectInput
 *
 * Check input_device.h to see interface this uses.
 */
#if USE_DINPUT
#define LOG_TAG "input_dinput"
#include "scc/utils/logging.h"
#include "scc/utils/assert.h"
#include "scc/utils/container_of.h"
#include "daemon.h"
#include <windows.h>
#include <winbase.h>
#include <InitGuid.h>
#include <dinput.h>
static IDirectInput8A* di;

typedef struct DInputInputDevice {
	InputDevice					dev;
	LPDIRECTINPUTDEVICE8		d8;
	struct InputInterruptData {
		sccd_input_read_cb		cb;
		void*					userdata;
	} 					idata;
} DInputInputDevice;

typedef LIST_TYPE(DInputInputDevice) InputDeviceList;
static InputDeviceList devices_with_iterupts;
static HWND input_window = 0;

static void sccd_input_dinput_mainloop(Daemon* d);


void sccd_input_dinput_init() {
	Daemon* d = get_daemon();
	devices_with_iterupts = list_new(DInputInputDevice, 32);
	ASSERT(d->mainloop_cb_add(&sccd_input_dinput_mainloop));
	ASSERT(devices_with_iterupts != NULL);
	if (DI_OK != DirectInput8Create(GetModuleHandle(NULL),
						DIRECTINPUT_VERSION, &IID_IDirectInput8A, (void**)&di, NULL)) {
		FATAL("dinput initialization failed");
	}
	LOG("dinput initialization done");
}


void sccd_input_dinput_close() {
	// TODO: What here?
	// TODO: Windows manages most of stuff around
}



static void sccd_input_dinput_dev_close(InputDevice* _dev) {
	DInputInputDevice* dev = container_of(_dev, DInputInputDevice, dev);
	IDirectInputDevice8_Unacquire(dev->d8);
	IDirectInputDevice8_Release(dev->d8);
	list_remove(devices_with_iterupts, dev);
	free(dev);
}

static bool sccd_input_dinput_interupt_read_loop(InputDevice* _dev, uint8_t endpoint, int length, sccd_input_read_cb cb, void* userdata) {
	DInputInputDevice* dev = container_of(_dev, DInputInputDevice, dev);
	
	if (dev->idata.cb != NULL) {
		LERROR("Only one input_read_cb can be attached to dinput device");
		return false;
	}
	if (length != sizeof(DIJOYSTATE2)) {
		LERROR("Invalid length supplied to interupt_read_loop. "
				"Only sizeof(DIJOYSTATE2) == %li is supported",
				sizeof(DIJOYSTATE2));
		return false;
	}
	
	if (!list_allocate(devices_with_iterupts, 1)) {
		// OOM
		LERROR("Out of memory");
		return false;
	}
	dev->idata.cb = cb;
	dev->idata.userdata = userdata;
	list_add(devices_with_iterupts, dev);
	return true;
}

static LRESULT CALLBACK sccd_input_dinput_wndproc(HWND window, UINT msg, WPARAM w, LPARAM l) {
	return DefWindowProc (window, msg, w, l);
}

InputDevice* sccd_input_dinput_open(const InputDeviceData* idev) {
	struct Win32InputDeviceData* wdev = container_of(idev, struct Win32InputDeviceData, idev);
	const DIDEVICEINSTANCE* d8dev = (const DIDEVICEINSTANCE*)wdev->d8dev;
	if (input_window == NULL) {
		static WNDCLASS cls_data = {
			.style = CS_NOCLOSE,
			.lpfnWndProc = sccd_input_dinput_wndproc,
			.hIcon = NULL,
			.hCursor = NULL,
			.hbrBackground = NULL,
			.lpszClassName = TEXT("scc-daemon-dinput-window")
		};
		cls_data.hInstance = GetModuleHandle(NULL);
		ATOM cls = RegisterClass(&cls_data);
		if (cls == 0) {
			LERROR("RegisterClass failed");
			return NULL;
		}
		input_window = CreateWindow(
				TEXT("scc-daemon-dinput-window"),
				TEXT("scc-daemon-dinput-window"),
				0,				// dwStyle
				0, 0,			// Position
				1, 1,			// Size
				HWND_MESSAGE,	// Parent (message-only window)
				NULL,			// Menu
				GetModuleHandle(NULL),
				NULL			// lpParam, no effing idea what it is
		);
		if (input_window == NULL) {
			LERROR("CreateWindow failed");
			return NULL;
		}
	}
	
	DInputInputDevice* dev = malloc(sizeof(DInputInputDevice));
	if (dev == NULL)
		// OOM
		return NULL;
	dev->d8 = NULL;
	dev->idata.cb = NULL;
	if (DI_OK != IDirectInput8_CreateDevice(di, &d8dev->guidInstance, &dev->d8, NULL)) {
		LERROR("IDirectInput8_CreateDevice failed");
		goto sccd_input_dinput_open_cleanup;
	}
	if (DI_OK != IDirectInputDevice8_SetDataFormat(dev->d8, &c_dfDIJoystick2)) {
		LERROR("IDirectInputDevice8_SetDataFormat failed");
		goto sccd_input_dinput_open_cleanup;
	}
	if (DI_OK != IDirectInputDevice8_SetCooperativeLevel(dev->d8, input_window, DISCL_BACKGROUND|DISCL_EXCLUSIVE)) {
		LERROR("IDirectInputDevice8_SetCooperativeLevel failed");
		goto sccd_input_dinput_open_cleanup;
	}
	if (DI_OK != IDirectInputDevice8_Acquire(dev->d8)) {
		LERROR("IDirectInputDevice8_Acquire failed");
		goto sccd_input_dinput_open_cleanup;
	}
	
	*((Subsystem*)(&dev->dev.sys)) = DINPUT;
	dev->dev.close = sccd_input_dinput_dev_close;
	dev->dev.claim_interfaces_by = NULL;
	dev->dev.interupt_read_loop  = sccd_input_dinput_interupt_read_loop;
	dev->dev.hid_request = NULL;
	dev->dev.hid_write = NULL;
	return &dev->dev;
	
sccd_input_dinput_open_cleanup:
	if (dev != NULL) {
		IDirectInputDevice8_Release(dev->d8);
		free(dev);
	}
	return NULL;
}


static void sccd_input_dinput_mainloop(Daemon* d) {
	static DIJOYSTATE2 state;
	FOREACH_IN(DInputInputDevice*, dev, devices_with_iterupts) {
		if (DIERR_INPUTLOST == IDirectInputDevice8_Poll(dev->d8))
			goto sccd_input_dinput_mainloop_device_lost;
		HRESULT r = IDirectInputDevice8_GetDeviceState(dev->d8,
											sizeof(DIJOYSTATE2), &state);
		if (r == DIERR_INPUTLOST)
			goto sccd_input_dinput_mainloop_device_lost;
		else if (r != DI_OK) {
			switch (r) {
			case DIERR_INVALIDPARAM:
				LERROR("GetDeviceState error: DIERR_INVALIDPARAM");
				break;
			case DIERR_NOTACQUIRED:
				LERROR("GetDeviceState error: DIERR_NOTACQUIRED");
				break;
			case DIERR_NOTINITIALIZED:
				LERROR("GetDeviceState error: DIERR_NOTINITIALIZED");
				break;
			case E_PENDING:
				LERROR("GetDeviceState error: E_PENDING");
				break;
			default:
				LERROR("GetDeviceState error: %i", r);
			}
			continue;
		}
		dev->idata.cb(d, &dev->dev, 0, (const uint8_t*)&state, dev->idata.userdata);
		continue;
sccd_input_dinput_mainloop_device_lost:
		LERROR("Device lost");
		dev->idata.cb(d, &dev->dev, 0, NULL, dev->idata.userdata);
	}
}


static char fake_syspath_buffer[1024];
static struct Win32InputDeviceData wdev = {
	.idev = { .subsystem = DINPUT, .path = fake_syspath_buffer }
};

BOOL CALLBACK d8_enum_devices_cb(const DIDEVICEINSTANCE* d8dev, void* trash_) {
	sccd_device_monitor_win32_fill_struct(&wdev);
	if (strstr(d8dev->tszProductName, "XBOX") != NULL) {
		// Desperatelly ignoring those to prevent SCC hooking into itself
		// and causing infinite loop of madness
		return DIENUM_CONTINUE;
	}
	
	LPOLESTR guid_str;
	if (S_OK != StringFromCLSID(&d8dev->guidInstance, &guid_str))
		return DIENUM_CONTINUE;
	snprintf(fake_syspath_buffer, 1024, "/win32/dinput/%ls", guid_str);
	CoTaskMemFree(guid_str);
	
	wdev.d8dev = (void*)d8dev;
	wdev.product = 0;
	wdev.bus = 0;
	wdev.dev = 0;
	wdev.idx = -1;
	
	sccd_device_monitor_new_device(get_daemon(), &wdev.idev);
	return DIENUM_CONTINUE;
}

void sccd_input_dinput_rescan() {
	IDirectInput8_EnumDevices(di, DI8DEVCLASS_GAMECTRL, d8_enum_devices_cb, NULL, DIEDFL_ATTACHEDONLY);
}


#endif
