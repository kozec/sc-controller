/**
 * SC Controller - Mapper
 * 
 * Mapper takes inputs from Controller, applies them to apropriate Action
 * taken from Profile and does actual work.
 */
#pragma once
#include "scc/controller.h"
#include <stdbool.h>
#include <stdint.h>

typedef struct Mapper Mapper;
typedef struct Profile Profile;
typedef void (*MapperScheduleCallback)(Mapper* m, void* userdata);
typedef uintptr_t TaskID;

struct Mapper {
	/**
	 * Determines type of mapper implementation.
	 * Should be unique for every implementation.
	 */
	const char*			type;
	/** Returns controller flags of assigned controller (or 0 if there is none) */
	ControllerFlags		(*get_flags)(Mapper* m);
	/** Sets controller used by mapper. */
	void				(*set_controller)(Mapper* m, Controller* c);
	/**
	 * Sets profile.
	 * If 'cancel_effects' is true, mapper should automatically cancel
	 * all long-running effects they may have created before profile is set.
	 * For example, it should stop any active rumble.
	 */
	void				(*set_profile)(Mapper* m, Profile* p, bool cancel_effects);
	/** Returns profile assigned by set_profile, without increasing its reference count */
	Profile*			(*get_profile)(Mapper* m);
	/**
	 * Returns controller assigned to this mapper, or NULL if there is none.
	 * Returned value has to stay allocated at least as long Mapper is, or
	 * until set_controller method is called.
	 */
	Controller*			(*get_controller)(Mapper* m);
	void				(*set_axis)(Mapper* m, Axis axis, AxisValue v);
	/** Schedules mouse movement to be done at end of input processing */
	void				(*move_mouse)(Mapper* m, double dx, double dy);
	/** Schedules mouse wheel move to be done at end of input processing */
	void				(*move_wheel)(Mapper* m, double dx, double dy);
	/**
	 * KeyPress emulates pressing key on virtual keyboard or button on
	 * key_press mouse or gamepad. Virtual device to use is determined from
	 * keycode.
	 *
	 * If release_press is set to true and virtual button is already pressed,
	 * implementation _may_ simulate releasing and pressing it again. It also
	 * _may_ keep counter so virtual button is released only after number
	 * of 'presses' matches number of 'releases'. This is not strictly necessary.
	 */
	void				(*key_press)(Mapper* m, Keycode b, bool release_press);
	/** Releases virtual button. See key_press for details. */
	void				(*key_release)(Mapper* m, Keycode b);
	
	/**
	 * Returns true if specified pad is being touched.
	 * May randomly return False for aphephobic pads.
	 */
	bool				(*is_touched)(Mapper* m, PadStickTrigger pad);
	/**
	 * was_touched works as is_touched, but returns true if pad *was* touched
	 * in last known (not current) state.
	 *
	 * This is used as:
	 * is_touched() and not was_touched() -> pad was just pressed
	 * not is_touched() and was_touched() -> pad was just released
	 */
	bool				(*was_touched)(Mapper* m, PadStickTrigger pad);
	/** Returns true if button is pressed */
	bool				(*is_pressed)(Mapper* m, SCButton button);
	/** Returns true if button was pressed in previous known state */
	bool				(*was_pressed)(Mapper* m, SCButton button);
	// TODO: Is this needed?
	// get_pressed_button
	// set_button
	// set_was_pressed
	
	/**
	 * Returns true if button on virtual mouse, keyboard or gamepad is believed
	 * to be pressed.
	 */
	bool				(*is_virtual_key_pressed)(Mapper* m, Keycode key);
	
	/**
	 * Called when daemon is killed or USB dongle is disconnected.
	 * Sends button release event for every virtual button that is still being
	 * pressed.
	 */
	void				(*release_virtual_buttons)(Mapper* m);
	/**
	 * Resets (recalibrates) gyro position so current position of physical
	 * gamepad is considered as "no rotation"
	 */
	void				(*reset_gyros)(Mapper* m);
	/**
	 * Handles 'special action'.
	 * Actual type of sa_data changes from action type to action type.
	 * See special_action.h for more info.
	 *
	 * This method may be set to NULL, in which case, mapper doesn't
	 * support special actions. If non-null, method should return true for
	 * every supported and false for every unsupported action.
	 */
	bool				(*special_action)(Mapper* m, unsigned int sa_action_type, void* sa_data);
	/**
	 * Plays haptic effect on controller assotiated with this mapper.
	 * If there is no controller assotiated or controller lacks support for
	 * rumble effects, this method should simply do nothing.
	 */
	void				(*haptic_effect)(Mapper* m, HapticData* hdata);
	
	/**  Called from driver code when input is recieved on physical gamepad */
	void				(*input)(Mapper* m, ControllerInput* i);
	/**
	 * Schedules function to be called after given delay.
	 * If any kind of multithreading is used, it has to be guaranteed that
	 * there is no race condition allowing more than one scheduled task
	 * or input method being processed at same time.
	 *
	 * Note that it's not guaranteed that callback will be called.
	 * That may not be a case for example if profile changes before callback
	 * is executed.
	 *
	 * Callback will be called from main loop.
	 * 'delay' is in milliseconds. It can be zero, in which case callback will be called ASAP.
	 *
	 * Returns task_id that can be used to cancel task or 0 in case of error.
	 */
	TaskID				(*schedule)(Mapper* m, uint32_t delay,
						MapperScheduleCallback callback, void* userdata);
	/**
	 * Cancels task scheduled by 'schedule'
	 */
	void				(*cancel)(Mapper* m, TaskID task_id);
};

