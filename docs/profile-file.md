SC-Controller profile file specification
----------------------------------------

Profile file contains json-encoded dictonary with specific keys. Missing keys are substituted with defaults, unknown keys are ignored. See [Desktop.sccprofile](../default_profiles/Desktop.sccprofile) for example.

Root dictonary has to contain following keys:
- `buttons`			- contains subkey for controller buttons. See [buttons](#buttons).
- `pad_left`		- sets action executed when finger is moved on left touchpad.
- `pad_right`		- ... when finger is moved on right touchpad.
- `stick`			- ... when stick angle is changed.
- `trigger_left`	- ... when left trigger value is changed.
- `trigger_right`	- ... when right trigger value is changed.
- `gyro`			- ... when gyroscope reading changes. Gyroscope in is activated only if this key is set to something else than `NoAction`
- `menus`			- stores menus saved in profile. See [menus](#menus).
- `version`			- profile file version. Current version is _1_. See If not pressent, _0_ is assumed. If profile file version is lower than expected, automatic conversion may happen. This conversion is in-memory only, but changing and saving such profile in GUI will save converted data.

See [actions.md](actions.md) file for list of possible actions.


## <A name="Action_definition"></a>Action definition
Action definition is dictionary containing `action` key and optional `name` key. Value assigned to `action` describes action to be executed.

For example,

	{
	  "trigger_left": {
	    "action": "axis(Axes.ABS_Z)",
	    "name": "Aim",
	}}

assigns `axis` action with *Axes.ABS_Z* parameter to left trigger.


## <a name="buttons"></a>Buttons
`buttons` is dictionary with keys for each gamepad button.
Possible keys are:

- `X`, `Y`, `A` and `B` for colored buttons
- `C` for Steam button in center
- `BACK` and `START` for small "( &lt; )" and "( &gt; )" buttons
- `LB` and `RB` for left and right bumper
- `LPADPRESS`, `RPADPRESS` and `STICKPRESS` for presing pads or stick.

All keys are optional. Value for each key is [action definition](#Action_definition)

Example:

	"buttons": {
	  "A":    { "action": "button(Keys.BTN_WEST)",  }, 
	  "B":    { "action": "osd('Hello world!')" }, 
	  "BACK": { "action": "button(Keys.KEY_LEFTCTRL) and button(Keys.KEY_A)" }, 
	}


## <a name="menus"></a>Menus
`menus` is dictionary with menus stored along with profile. Keys are IDs of
menus; Menu ID can contain any characters but dots (".") and slashes ("/").

Value for each key is same as root list in [menu file](menu-file.md)
