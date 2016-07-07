### In this document
- [Custom Action page](#examples1)
- [List of all known actions](#actions)
- [Macros and operators](#macros)
- [Profile file examples](#examples2)

# <a name="examples1"></a>Custom Action page examples

- To do two or more things at once, type `action() and action()`
- To do two or more things in sequence, type `action() ; action()`
- Typing second action on new line is same thing as using `and`

#### Press button repeadedly, rapid fire mode
`repeat(button(BTN_A))` (see [repeat](#repeat), [button](#button))

#### Press Alt+F4
`button(KEY_LEFTALT) and button(KEY_F4)`

#### Press multiple buttons in sequence
`button(BTN_A) ; button(BTN_X); button(BTN_B)`

#### Press button and hold it for set delay
`press(BTN_A) ; sleep(0.5); release(BTN_B)` (see [press](#press), [sleep](#sleep), [release](#release))


# <a name="actions"></a>Actions

#### <a name="button"></a> button(button1 [, button2 = None, minustrigger = -16383, plustrigger = 16383 ])
- For stick or pad, when it is moved over 'minustrigger', 'button1' is pressed;
  When it is moved back, 'button1' is released. Similary, 'button2' is pressed
  and released when stick (or finger on pad) moves over 'plustrigger' value
- For trigger, when trigger value goes over 'plustrigger', 'button2' is pressed;
  then, when trigger value goes over 'minustrigger', 'button2' is released and
  replaced with 'button1'. Whatever button was emulated by trigger, it is
  released when trigger is released.
  
  Note that 'button2' is always optional.


#### <a name="mouse"></a> mouse(axis)
Controls mouse movement or scroll wheel.

- For stick, lets cursor or mouse wheel to be controlled by stick tilt.
- For pad, does same thing as 'trackball'. You can set pad to move mouse only
  in one axis using this.
- For gyroscope, controls mouse with changes in controller pitch and roll/yaw.
  Axis parameter should be either YAW or ROLL (constants) and decides which
  gyroscope axis controls X mouse axis.
- For wheel controlled by pad, emulates finger scroll.
- For button, pressing button maps to single movement over mouse axis or
  single step on scroll wheel.


#### <a name="circular"></a> circular(axis)
Controls scroll wheel by scrolling finger around pad.
Axis should be Rels.REL_WHEEL or Rels.REL_HWHEEL.


#### <a name="area"></a> area(x1, y1, x2, y2), winarea(x1, y1, x2, y2)
Creates 1:1 mapping between finger position on pad and mouse position in
specified screen area. Coordinates are in pixels with (0,0) on top,left corner.
Negative number can be used to count from other side of screen.

`winarea` does same thing but with position relative to current window instead of entire screen.


#### <a name="relarea"></a> relarea(x1, y1, x2, y2), relwinarea(x1, y1, x2, y2)
Creates 1:1 mapping between finger position on pad and mouse position in
specified screen area. Coordinates are fractions of screen width and height,
(0,0) is top,left and (1,1) bottom,right corner of screen.

`relwinarea` does same thing but with position relative to current window instead of entire screen.


#### <a name="gyro"></a> gyro(axis1 [, axis2 [, axis3]])
Maps *changes* in gyroscope pitch, yaw and roll movement into movements of gamepad stick.
Can be used to map gyroscope to camera when camera can be controlled only with analog stick.


#### <a name="gyroabs"></a> gyroabs(axis1 [, axis2 [, axis3]])
Maps absolute gyroscope pitch, yaw and roll movement into movements of gamepad stick.
Can bee used ot map gyroscope to movement stick or to use controller as racing wheel.


#### <a name="trackpad"></a> trackpad()
Available only for pads. Acts as trackpad - sliding finger over the pad moves the mouse.


#### <a name="trackball"></a> trackball()
Available only for pads. Acts as trackball.


#### <a name="axis"></a> axis(id [, min = -32767, max = 32767 ])
- For button, pressing button maps to moving axis full way to 'max'.
  Releasing button returns emulated axis back to 'min'.
- For stick or pad, simply maps real axis to emulated
- For trigger, maps trigger position to to emulated axis. Note that default
  trigger position is not in middle, but in minimal possible value.


#### <a name="dpad"></a> dpad(up, down, left, right)
Emulates dpad. Touchpad is divided into 4 triangular parts and when user touches
touchped, action is executed depending on finger position.
Available only for pads and sticks; for stick, works by translating
stick position, what probably doesn't yields expected results.


#### <a name="dpad"></a> dpad8(up, down, left, right, upleft, upright, downleft, downright)
Same as dpad, with more directions.


#### <a name="press"></a> press(button)
Presses button and leaves it pressed.

#### <a name="release"></a> release(button)
Releases pressed button.

#### <a name="tap"></a> tap(button)
Presses button for a short while.
If button is already pressed, releases it, taps it and presses it
again in quick sequence.

#### <a name="profile"></a> profile(name)
Loads another profile


#### <a name="shell"></a> shell(command)
Executes command on background


#### <a name="turnoff"></a> turnoff()
Turns controller off


#### <a name="osd"></a> osd([timeout=5], text)
Displays text in OSD.


#### <a name="menu"></a> menu(menu [, confirm_button=A [, cancel_button=B [, show_with_release=False]]]])
Displays OSD menu.
'confirm_button' and 'cancel_button' sets which gamepad button should be used to
confirm/cancel menu. Additionaly, 'confirm_button' can be set to SAME (constant),
in which case menu will be closed and selected item choosen when button used to
display menu is released.

If 'show_with_release' is set to true, menu is displayed only after button
is released.

'menu' can be either id of menu defined in same profile file or filename
relative to `~/.config/scc/menus` or `/usr/share/scc/default_menus/`, whichever
exists, in that order.


#### <a name="gridmenu"></a> gridmenu(menu [, confirm_button=A [, cancel_button=B [, show_with_release=False]]]])
Same as `menu`, but displays items in grid.


#### <a name="radialmenu"></a> radialmenu(menu [, confirm_button=A [, cancel_button=B [, show_with_release=False]]]])
Same as `menu`, but displays items in radial menu.


#### <a name="keyboard"></a> keyboard()
Displays on-screen keyboard

# Modifiers:

#### <a name="click"></a> click(action)
Used to create action that occurs only if pad or stick is pressed.
For example, `click(dpad(...))` set to pad will create dpad that activates
buttons only when pressed.


#### <a name="mode"></a> mode(button1, action1, [button2, action2... buttonN, actionN] [, default] )
Defines mode shifting. If physical buttonX is pressed, actionX is executed.
Optional default action is executed if none from specified buttons is pressed.


#### <a name="doubleclick"></a> doubleclick(doubleclick_action [, normal_action [, timeout ]])
Executes action if user double-clicks button.
Optional normal_action parameter specifies action that is executed when user
click button only once. Optional time arguments modifies maximum delay in 
doubleclick and in effect sets delay before normal action is executed.

#### <a name="hold"></a> hold(hold_action [, normal_action [, timeout ]])
Executes action if user holds button for longer time.
Optional normal_action parameter specifies action that is executed when user
click button shortly. Optional time arguments modifies how long "longer time" is.

Hold and doubleclick can be combined together by writing
`hold([time,] hold_action, doubleclick(doubleclick_action, normal_action))`


#### <a name="sens"></a> sens(x_axis [, y_axis [, z_axis]], action)
Modifies sensitivity of physical stick or pad.


#### <a name="feedback"></a> feedback(side, [amplitude=256 [, frequency=4 [, period=100 [, count=1 ]]]], action)
Enables haptic feedback for specified action, if action supports it.
Side has to be one of LEFT, RIGHT or BOTH. All remaining numbers can be anything
from 1 to 32768, but note that setting count to large number will start long
running feedback that you may not be able to stop.

'frequency' is used only when emulating touchpad and describes how many pixels
should mouse travell between two feedback ticks.


#### <a name="deadzone"></a> deadzone(lower, [upper, ] action)
Enables deadzone on trigger, pad or stick.


#### <a name="osd"></a> osd([timeout=5], action)
Enables on screen display for action. In most cases just displays action
description in OSD and executes it normally.
Works only if executed by pressing physical button or with `dpad`. Otherwise
just executes child action.


#### <a name="name"></a> name(name, action)
Allow inline setting of action name


# Shortcuts:
#### <a name="raxis"></a> raxis(id)
Shortcut for `axis(id, 32767, -32767)`, that is call to axis with min/max values
reversed. Effectively inverted axis mapping.

#### <a name="hatup"></a> hatup(id)
Shortcut for `axis(id, 0, 32767)`, emulates moving hat up or pressing 'up'
button on dpad.

#### <a name="hatdown"></a> hatdown(id)
Shortcut for `axis(id, 0, -32767)`, emulates moving hat down or pressing 'down'
button on dpad.

#### <a name="hatleft"></a> hatleft(id), hadright(id)
Same thing as hatup/hatdown, as vertical hat movement and left/right dpad
buttons are same events on another axis


# <a name="macros"></a>Macros and operators

#### <a name="and"></a> and - executing actions at once
It is possible to join two (or more) actions with `and` keyword (or newline) to have them executed together.
- `button(KEY_LEFTALT) and button(KEY_F4)` presses Alt+F4

#### <a name="semicolon"></a> semicolon - sequence (macro)
When `;` is placed between actions, they are executed as sequence.
- `hatup(ABS_Y); hatup(ABS_Y); button(BTN_B); button(BTN_A)` presses 'UP UP B A' on gamepad, as fast as possible
- `button(KEY_A); button(KEY_B); button(KEY_C)` types 'abc'.

#### <a name="type"></a> type('text')
Special type of macro where keys to press are specified as string.
Basically, writing `type("iddqd")` is same thing as `button(KEY_I) ; button(KEY_D) ;
button(KEY_D); button(KEY_Q); button(KEY_D)`, just much shorter.

#### <a name="sleep"></a> sleep(x)
To insert pause between macro actions, use sleep() action.
- `button(KEY_A); button(KEY_B); sleep(1.0); button(KEY_C)` types 'ab', waits 1s and types 'c'

#### <a name="repeat"></a> repeat(action)
Turbo / rapid fire mode. Repeats macro (or even single action) until physical button is released. Macro is always played to end, even if button is released before macro is finished.
- `repeat(button(BTN_X))` deals with "mash X to not die" events in some games.

#### <a name="cycle"></a> cycle(action1, action2...)
Executes different action every time when button is pressed (action1 upon first press, action2 with second, etc.)
Works only on buttons.


# <a name="examples2"></a>Examples for profile file
Emulate key presses based on stick position
```
"stick" : {
	"X"		: { "action" : "pad(KEY_A, KEY_D)" },
	"Y"		: { "action" : "key(KEY_W, KEY_S)" },
```


Emulate left/right stick movement with X and B buttons
```
"buttons" : {
	"B"      : { "action" : "axis(ABS_X, 0, 32767)" },
	"X"      : { "action" : "axis(ABS_X, 0, -32767)" },
```

Emulate dpad on left touchpad, but act only when dpad is pressed
```
"left_pad" : {
	"action" : "click( dpad('hatup(ABS_HAT0Y)', 'hatdown(ABS_HAT0Y)', 'hatleft(ABS_HAT0X)', 'hatright(ABS_HAT0X)' ) )"
}
```

Emulate button A when left trigger is half-pressed and button B when
it is pressed fully
```
"triggers" : {
	"LEFT"  : { "action" : "pad(BTN_A, BTN_B)" },
```