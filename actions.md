# Actions

#### key(key1 [, key2 = None, minustrigger = -16383, plustrigger = 16383 ])
- For button, simply maps to 'key1' press.
- For stick or pad, when it is moved over 'minustrigger', 'key1' is pressed;
  When it is moved back, 'key1' is released. Similary, 'key2' is pressed and
  released when stick (or finger on pad) moves over 'plustrigger' value
- For trigger, when trigger value goes over 'plustrigger', 'key2' is pressed;
  then, when trigger value goes over 'minustrigger', 'key2' is released and
  replaced with 'key1'. Whatever keypress was emulated by trigger, it is
  released when trigger is released.
  
  Note that 'key2' is optional.


### mouse(axis [, speed = 1, acceleration = 0 ])
Controls mouse movement or scroll wheel.

- For stick, lets cursor to be controlled by stick tilt.
- For pad, emulates stick and then controls cursor by emulated stick.
  Use trackpad() instead.
- For trigger, moves mouse in one direction with speed depending on how much
  is trigger pressed.
- For button, pressing button maps to single movement over mouse axis or
  single step on scroll wheel.


### trackpad([ speed = 1 ])
Available only for pads. Acts as trackpad - sliding finger over the pad moves the mouse.


### trackball([ speed = 1 ])
Available only for pads. Acts as trackball.

### wheel([ trackball = False, speed = 1 ])
Available only for pads. Emulates mouse scroll wheel.


### button(button1 [, button2 = None, minustrigger = -16383, plustrigger = 16383 ])
Controls gamepad and mouse buttons.
Works in same way as key(), but for buttons.


#### axis(id [, min = -32767, max = 32767 ])
- For button, pressing button maps to moving axis full way to 'max'.
  Releasing button returns emulated axis back to 'min'.
- For stick or pad, simply maps real axis to emulated
- For trigger, maps trigger position to to emulated axis. Note that default
  trigger position is not in middle, but in minimal possible value.


#### dpad(up, down, left, right)
Emulates dpad. Touchpad is divided into 4 triangular parts and when user touches
touchped, action is executed depending on finger position.
Available only for pads and sticks; for stick, works by translating
stick position, what probably doesn't yields expected results.


#### click()
Used to create action, that occurs only if pad or stick is pressed.
For example, `click() and axis(Axes.ABS_X)` set to pad axis will move
emulated stick only if pad is pressed.

- For button or trigger, always returns True
- For stick or pad returns True if stick or pad is pressed down
- For trigger returns True if trigger is pressed all the way down
  (it actually clicks)


# Shortcuts:
#### raxis(id)
Shortcut for `axis(id, 32767, -32767)`, that is call to axis with min/max values
reversed. Effectively inverted axis mapping.

#### hatup(id)
Shortcut for `axis(id, 0, 32767)`, emulates moving hat up or pressing 'up'
key on dpad.

#### hatdown(id)
Shortcut for `axis(id, 0, -32767)`, emulates moving hat down or pressing 'down'
key on dpad.

#### hatleft(id), hadright(id)
Same thing as hatup/hatdown, as vertical hat movement and left/right dpad
buttons are same events on another axis



# Examples:
Emulate key and button presses based on stick position
```
"stick" : {
	"X"		: { "action" : "pad(Keys.BTN_X, Keys.BTN_B)" },
	"Y"		: { "action" : "key(Keys.KEY_A, Keys.KEY_B)" },
```


Emulate left/right stick movement with X and B buttons
```
"buttons" : {
	"B"      : { "action" : "axis(Axes.ABS_X, 0, 32767)" },
	"X"      : { "action" : "axis(Axes.ABS_X, 0, -32767)" },
```

Emulate dpad on left touchpad, but act only when dpad is pressed
```
"left_pad" : {
	"action" : "click() and dpad('hatup(Axes.ABS_HAT0Y)', 'hatdown(Axes.ABS_HAT0Y)', 'hatleft(Axes.ABS_HAT0X)', 'hatright(Axes.ABS_HAT0X)' )"
}
```

Emulate button A when left trigger is half-pressed and button B when
it is pressed fully
```
"triggers" : {
	"LEFT"  : { "action" : "pad(Keys.BTN_A, Keys.BTN_B)" },
```