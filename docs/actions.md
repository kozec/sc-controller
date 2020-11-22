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

#### <a name="button"></a> button(button1 [, button2 = None ])
- For button, simply maps real button to emulated
- For stick or pad, 'button1' is pressed when stick or finger on pad is moved
  to up or left and 'button2' when to down or right.
  Using [dpad](#dpad) may be better for such situations.
- For trigger, when trigger is pressed, but until it clicks, 'button2' is
  pressed. When trigger clicks 'button2' is released and replaced by 'button1'.
  If only 'button1' is set, trigger acts as big button.
  
  Note that 'button2' is always optional.


#### <a name="mouse"></a> mouse(axis)  

- For stick, lets cursor or mouse wheel to be controlled by stick tilt.
- For pad, acts as trackpad - sliding finger over pad moves the mouse.
  If set to *REL_WHEEL* or *REL_HWHEEL*, emulates finger scroll.
  You can use `ball(mouse)` to emulate trackball.
- For gyroscope, controls mouse with changes in controller pitch and roll/yaw.
  Axis parameter should be either YAW or ROLL (constants) and decides which
  gyroscope axis controls X mouse axis.
- For button, pressing button maps to single movement over mouse axis or
  single step on scroll wheel.


#### <a name="mouseabs"></a> mouseabs(axis)

- For stick, lets cursor or mouse wheel to be controlled by stick tilt.
- For pad, distance from center of pad controls speed of mouse movement
- For gyroscope, please, use gyroabs action.


#### <a name="trackpad"></a> trackpad(axis)
Merged with [mouse](#mouse), does same thing.


#### <a name="axis"></a> axis(id [, min = -32767, max = 32767 ])
- For button, pressing button maps to moving axis full way to 'max'.
eleasing button returns emulated axis back to 'min'.
- For stick or pad, simply maps real axis to emulated
- For trigger, maps trigger position to to emulated axis. Note that default
  trigger position is not in middle, but in minimal possible value.


#### <a name="dpad"></a> dpad([diagonal_rage,] up, down, left, right)
Emulates dpad. Touchpad is divided into 8 triangular parts. When the user
touches the touchpad, action is executed depending on finger position.

'diagonal_rage' is specified in degrees (1 to 89). If not set, all parts are
sized equally, otherwise, diagonal parts are taking specified portion of pad
and rest is assigned to up/left/right/down portions.

Available only for pads and sticks.


#### <a name="dpad8"></a> dpad8([diagonal_rage,] up, down, left, right, upleft, upright, downleft, downright)
Same as dpad, with more directions.


#### <a name="ring"></a> ring([radius=0.5], inner, outer)
Defines outer and inner ring bindings. When distance of finger from center of
pad is smaller than 'radius', 'inner' action is activated, otherwise, 'outer'
takes place.

Unlike [dpad](#dpad), which executes actions as if they were bound to buttons,
ring works more like defining two actions on same pad with non-overlapping
deadzones.


#### <a name="area"></a> area(x1, y1, x2, y2), <a name="winarea"></a> winarea(x1, y1, x2, y2)
Creates 1:1 mapping between finger position on pad and mouse position in
specified screen area. Coordinates are in pixels with (0,0) on top,left corner.
Negative number can be used to count from other side of screen.

`winarea` does same thing but with position relative to current window instead of entire screen.


#### <a name="relarea"></a> relarea(x1, y1, x2, y2), <a name="relwinarea"></a> relwinarea(x1, y1, x2, y2)
Creates 1:1 mapping between finger position on pad and mouse position in
specified screen area. Coordinates are fractions of screen width and height,
(0,0) is top,left and (1,1) bottom,right corner of screen.

`relwinarea` does same thing but with position relative to current window instead of entire screen.


#### <a name="trigger"></a> trigger(press_level, [release_level, ] action)
Maps action to be executed as by button press when trigger is pressed through
'press_level'. Level goes from 0 to 255, where 255 is level after physical
trigger clicks.
Then, optionally, if trigger is pressed through 'release_level', action is
"released". If release_level is not set, action will be released only after
trigger value moves back beyond press_level.

It's possible to map multiple actions on different trigger levels using [and](#and).

Examples:

Hold right mouse button while trigger is being pressed, press left button when
trigger clicks. Right button is released only when trigger is fully released.
```
trigger(64, 255, button(BTN_RIGHT)) and trigger(255, button(BTN_LEFT))
```

Control left virtual trigger while trigger is being pressed and press left button
just before trigger clicks. If trigger clicks, press enter key and play feedback.
```
	trigger(64, 255, axis(ABS_Z))
and
	trigger(240, 254, button(BTN_LEFT))
and
	trigger(255, feedback(LEFT, button(KEY_ENTER)))
```

#### <a name="hipfire"></a> hipfire([partialpress_level, ][fullpress_level, ] partialpress_action, fullpress_action [, mode][, delay])
Maps two different actions to be executed when trigger is inside a defined range and meet predefined conditions.
Basically, the "partialpress_action" will be activated if the trigger is pressed passed the "partialpress_level" and it stays inside the range between this level and the "fullpress_level" until the "delay" ends, otherwise, the "fullpress_action" will be activated ALONE if the "fullpress_level" is reached before the "delay" ends.

The partial and full levels goes from 0 to 255, and the values 50 and 254 are used for "partialpress_level" and "fullpress_level", respectively, if none is passed.

The "mode" can be defined as described below and the "NORMAL" one is used if none is  passed.

Modes available:

 - NORMAL - if trigger is pressed beyond the "partialpress_level" and the timeout is reached, the "partialpress_action" is executed. If the "partialpress_action" was pressed it will only be released after the trigger return back beyond the "partialpress_level". The "fullpress_action" will be executed every time the "fullpress_level" is reached, but if this level is reached before the timeout the "partialpres_action" will not be triggered until releasing the trigger.
 - EXCLUSIVE - Acts similar to the previous mode, but the "fullpress_action" is only triggered if the "partialpres_action" was not triggered. Meaning it will only activate if the "fullpress_level" is reached before the timeout ends.
 - SENSIBLE - Acts similar to NORMAL, but after the "partialpress_action" is activated, releasing the trigger a little, will deactivate the action allowing it to be activated again more faster without needing to release the trigger back beyond the "partialpress_level". 

The "delay" is time window used to determine if the "partialpress_action" should or not be activated. 

Examples:

Hold right mouse button while trigger is being softly pressed and press left mouse button when trigger click, but will bypass the right mouse button and only press the left mouse button if the trigger is pressed very fast to the click.
```
hipfire(50, 254, button(BTN_RIGHT),button(BTN_LEFT), NORMAL, 0.20)
```

Press A if the trigger is pressed slowly and not reaches the click or press B if the trigger is pressed fast and reached the click, and will execute only one of this two actions.

```
hipfire(50, 254, button(KEY_A),button(KEY_B), EXCLUSIVE, 0.15)
```

#### <a name="gyro"></a> gyro(axis1 [, axis2 [, axis3]])
Maps *changes* in gyroscope pitch, yaw and roll movement into movements of gamepad stick.
Can be used to map gyroscope to camera when camera can be controlled only with analog stick.


#### <a name="gyroabs"></a> gyroabs(axis1 [, axis2 [, axis3]])
Maps absolute gyroscope pitch, yaw and roll movement into movements of mouse
or gamepad stick.
Can be used to map gyroscope to movement stick or to use controller as racing wheel.


#### <a name="resetgyro"></a> resetgyro()
Resets gyroscope offsets so current orientation is treated as neutral.


#### <a name="cemuhook"></a> cemuhook()
When set to gyro, outputs gyroscope data in way compatibile with Cemu, Citra and
other applications using CemuHookUDP motion provider protocol.


#### <a name="tilt"></a> gyro(front_down, front_up, tilt_left, tilt_right)
Maps tilting of gamepad into actions. When gamepad is tilt to one of for supported
sides, assigned action is executed as if by button press and then "released" after
gamepad is balanced again.


#### <a name="trackball"></a> trackball()
Split to [ball](#ball) modifier and [mouse](#mouse) action.

Typing `trackball` works as alias for `ball(mouse())`


#### <a name="XY"></a> XY(xaction, yaction)
Provides way to assign two different actions to two stick or pad axes.
This is automatically handled by GUI, so user usually doesn't need
to write it directly.


#### <a name="relXY"></a> relXY(xaction, yaction)
Works same as [XY](#XY), but treats position where pad is touched as "center"
of pad.


#### <a name="press"></a> press(button)
Presses button and leaves it pressed.


#### <a name="release"></a> release(button)
Releases pressed button.


#### <a name="tap"></a> tap(button, number=1)
Presses button for a short while, 'number' times.

If 'number' is greater than 1 (when double-tap is performed), tapped button
is kept press as long as physical button that started tap is pressed. For single
tap, virtual button is released right away.

If virtual button is already pressed before tapping, it is released first and
restored after tap, resulting in sequence of "release - press - release - press"


#### <a name="profile"></a> profile(name)
Loads another profile


#### <a name="shell"></a> shell(command)
Executes command on background


#### <a name="turnoff"></a> turnoff()
Turns controller off


#### <a name="restart"></a> restart()
Restarts scc-daemon. Don't use unless you have good reason to.


#### <a name="led"></a> led(brightness)
Sets brightness of controller led. 'Brightness' is percent in 0 to 100 range.


#### <a name="osd"></a> osd([timeout=5, [size=3]], text)
Displays message in OSD.

'timeout' sets for how many seconds should message stay visible. Value of 0 has
special meaning and leaves message displayed indefinitely, until profile is
changed or [clearosd](#clearosd) action is used.

'size' sets size of font on message. Only three options are supported right now,
3 for "default size", 2 for "smalller" and 1 for "small".



#### <a name="clearosd"></a> clearosd()
Clears all windows from OSD layer. Cancels all menus, clears all messages,
hides on screen keyboard.

Does _not_ clear OSD windows created using command line tools.


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


#### <a name="hmenu"></a> hmenu(menu [, confirm_button=A [, cancel_button=B [, show_with_release=False]]]])
Same as `menu`, but packed in one row.


#### <a name="gridmenu"></a> gridmenu(menu [, confirm_button=A [, cancel_button=B [, show_with_release=False]]]])
Same as `menu`, but displays items in grid.


#### <a name="radialmenu"></a> radialmenu(menu [, confirm_button=A [, cancel_button=B [, show_with_release=False]]]])
Same as `menu`, but displays items in radial menu.


#### <a name="quickmenu"></a> quickmenu(menu)
Special kind of menu controled by buttons instead of stick. Every item has
assigned button and user selects it by pressing that button.

Fast to use, but is limited to 6 items at most.


#### <a name="dialog"></a> dialog([ confirm_button=A [, cancel_button=B ], ] text, action1, [action2... actionN])
Displays OSD dialog. Dialog works similary to horizontal menu and displays
text message above list of options.


#### <a name="keyboard"></a> keyboard()
Displays on-screen keyboard

# Modifiers:

#### <a name="click"></a> click(action)
Creates action action that occurs only if pad or stick is pressed.
For example, `click(dpad(...))` set to pad will create dpad that activates
buttons only when pressed.

#### <a name="pressed"></a> pressed(action)
Creates action that occurs for brief moment when button is pressed.
For example, `pressed(button(A))` will press and instantly release virtual
A button whenever physical button is pressed.

#### <a name="released"></a> released(action)
Creates action that occurs for brief moment when button is released.

#### <a name="touched"></a> pressed(action)
Creates action that occurs for brief moment when finger touches pad.

#### <a name="untouched"></a> released(action)
Creates action that occurs for brief moment when pad is released.

#### <a name="mode"></a> mode(button1, action1, [button2, action2... buttonN, actionN] [, default] )
Defines mode shifting. If physical buttonX is pressed, actionX is executed.
Optional default action is executed if none from specified buttons is pressed.


#### <a name="gestures"></a> gestures([precision=0,] gesture1, action1, [gesture2, action2... gestureN, actionN] )
If set to left or right pad, enables gesture recognition. If GestureX
is drawn, actionX is executed.

If 'precision' is set to 1.0, gesture has to be exact. Otherwise,
gestures resembling input with given precision are compared and
one that matches it most is used. At precision of 0.0, all gestures are considered.

<a name="gesture_format"></a>Gestures are encoded in string and it's
recommended to use GUI to record them. Nevertheless, format is simple:
- Each stroke in one of four directions is stored as single character.
- Characters are uppercase `U`, `D`, `L`, `R` for up, down, left, right
- Default stroke length is 1/3 of pad size.
- For stroke with twice of that length, characters is repeated twice
- Three times for stroke through entire pad, or even more for longer.
- If string starts with lowercase `i`, stroke length is ignored.


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


#### <a name="rotate"></a> rotate(angle, action)
Rotates input pad or stick input by given angle.


#### <a name="feedback"></a> feedback(side, [amplitude=256 [, frequency=4 [, period=100 [, count=1 ]]]], action)
Enables haptic feedback for specified action, if action supports it.
Side has to be one of LEFT, RIGHT or BOTH. All remaining numbers can be anything
from 1 to 32768, but note that setting count to large number will start long
running feedback that you may not be able to stop.

'frequency' is used only when emulating touchpad and describes how many pixels
should mouse travel between two feedback ticks.


#### <a name="ball"></a> ball([friction=10.0, [mass=80.0, ]] action)
Enables trackball mode. Moving finger over pad will keep repeating same action
with decreasing speed, based on set mass and friction, until virtual
'spinning ball' stops moving.


#### <a name="circular"></a> circular(action)
Designed to controls scroll wheel by scrolling finger around pad.
Can be used with any axis. For example,

`circular(axis(Axes.ABS_X))`

turns touchpad into small raing wheel.


#### <a name="circularabs"></a> circular(action)
Works as to `circular`, but instead of counting with finger movements,
translates exact position on dpad to axis value.


#### <a name="deadzone"></a> deadzone([mode,] lower, [upper, ] action)
Enables deadzone on trigger, pad or stick.
Mode defaults to 'CUT' and can be one of:

 - CUT     - if value is out of deadzone range, output value is zero
 - ROUND   - for values bellow deadzone range, output value is zero. For values
above range, output value is maximum allowed.
 - LINEAR  - input value is scaled, so entire output range is covered by
range of deadzone.
 - MINIMUM - any non-zero input value is scaled so entire input range is mapped
to range of deadzone. Zero on input is mapped to zero on output, so there is
area over which output "jumps" when stick is tilted.


#### <a name="smooth"></a> smooth([buffer=8, [multiplier=0.7, [filter=2, ]]] action)
Enables input smoothing. Position is computed as weighed average of last X
input positions with highest weight given to most recent position. If 'filter'
is above zero, movements bellow that value are ignored.


#### <a name="osd"></a> osd([timeout=5], action)
Enables on screen display for action. In most cases just displays action
description in OSD and executes it normally.
Works only if executed by pressing physical button or with `dpad`. Otherwise
just executes child action.


#### <a name="position"></a> position(x, y, action)
Specifies menu position on screen. X is position from left, Y from top. To
specify position from right or bottom, use negative values.


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


#### <a name="hatleft"></a> hatleft(id), <a name="hatright"></a> hatright(id)
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
