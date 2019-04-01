SCCDaemon Protocol specification
--------------------------------

To control running daemon instance, unix socket in user directory is used.
Controlling protocol uses case-sensitive messages terminated by newline. Message type and message arguments are delimited by `:`.

When new connection is accepted, daemon sends some info:

```
SCCDaemon
Version: 0.2.6
PID: 123456
Current profile: filename.sccprofile
Ready.
```

Connection is then held until client side closes it.

### Messages sent by daemon:

#### `Controller Count: n`
Informs about total number of connected controllers.
Always sent after `Controller:` messages

#### `Controller: controller_id type flags config_file`
Provides info about controller 'n'.
- `controller_id` is unique string identifier of controller (should stay same at
least until daemon exits) and doesn't contains spaces.
- `type` is string identifier (without spaces) of driver.
- `flags` describes controller features, such as having central touchpad.
See ControllerFlags definition in scc/constants.py for more info.
- `config_file` is None or file name of json-encoded file that can GUI use
to get additional data about controller (background image, button images, etc)
File name may be absolute path or just name of file in /usr/share/scc

This message is repeated for every connected controller and followed by
`Controller Count:` message. It is automatically sent to every client when
number of connected controllers changes. It is also sent automatically to
every new client.

#### `Controller profile: controller_id filename.sccprofile`
Sent to every client when profile file for any controller is loaded and used.
Also sent automatically to every new client.

#### `Current profile: filename.sccprofile`
Similar to `Controller profile:`, sent to every client when profile file for
first controller is loaded and used. Also sent automatically to every new client.

Unlike `Controller profile:`, this message is sent even if there is no
controller connected.

#### `Event: source values`
Sent to client that requested locking of source (that is button, pad or axis).

List of possible events:
- `Event: B 1` - Sent when button is pressed. *B* is button, is one of *SCButtons.\** constants.
- `Event: B 0` - Sent when button is released. *B* is button one of *SCButtons.\** constants.
- `Event: STICK x y` - Sent when stick position is changed. *x* and *y* are new values.
- `Event: LEFT x y` - Sent when finger on left pad is moved. *x* and *y* is new position.
- `Event: RIGHT x y` - Sent when finger on right pad is moved. *x* and *y* is new position.

#### `Error: message`
Sent to every client when error is detected. May be sent repeatedly to indicate
multiple errors, until all error condition is cleared.

After all errors are cleared, `Ready.` is sent to indicate that emulation works again.

#### `Fail: text`
Indicates error client that sent request.

#### `Gesture: side gesturestring`
Sent to client that requested gesture to be detected.

#### `OK.`
Indicates sucess to client that sent request.

### `OSD: tool param1 param2...`
Send to scc-osd-daemon when osd-related action is requested.
*tool* can be *'message'*, *'menu'*, *'hmenu'*, *'gridmenu'*,*'radialmenu'* or *'gesture'*
*params* are same as command-line arguments for scc-osd-* script with that name.

#### `PID: xyz`
Reports PID of *scc-daemon* instance. Automatically sent when connection is accepted.

#### `Ready.`
Automatically sent when connection is accepted to indicate that there is no error and daemon is working as expected.

#### `Reconfigured.`
Sent to all clients when daemon receives `Reconfigure.` message.

#### `SCCDaemon`
Just identification message, automatically sent when connection is accepted.
Can be either ignored or used to check if remote side really is *scc-daemon*.

#### `State: ....`
Sent to client as response to `State.` message. String after colon describes
current state of controller (such as pressed buttons and stick position...)
and is device-specific.

#### `Version: x.y.z`
Identifies daemon version. Automatically sent when connection is accepted.

## Commands sent from client

#### `Controller: controller_id`
By default, all messages sent from client are related to first connected
controller. This message changes which controller are following messages meant
for.

If controller with specified controller_id is known, daemon responds with `OK.`
Otherwise, `Fail: no such controller` error message is sent.

#### `Controller.`
Restores default state after controller is chosen.
Daemon responds with `OK.`

#### `Exit.`
Asks daemon to exit ASAP. Used on Windows instead of sending SIGTERM.
Daemon responds with `OK.`

#### `Gesture: side up_angle`
Requests gesture to be detected on one of pads. 'side' can be LEFT or RIGHT.
'up_angle' is angle in radians and sets how much should be gesture input
rotated.

Daemon always responds with `OK.` unless request cannot be parsed.
Then, when gesture detection is completed, daemon sends
`Gesture: side detectedgesture` message. If gesture detection fails for any
reason, sent gesture is empty.

#### `Led: brightness`
Sets brightness of controller led. 'Brightness' is percent in 0 to 100 range.
Daemon responds with `OK.`, unless 'brightness' cannot be parsed, in which case
`Fail: ...` with error message is sent.

#### `Lock: button1 button2...`
Locks physical button, axis or pad. Events from locked sources are not processed normally, but sent to client that initiated lock.

Only one client can have one source locked at one time. Second attempt to lock already locked source will fail and `Fail: cannot lock <button>` will be sent as response. Locking is done only if all requested sources are free and in such case, daemon responds with `OK.`

While source is locked, daemon keeps sending `Event: ...` messages every time when button is pressed, released, axis moved, etc...

Unlocking is done automatically when client is disconnected, or using `Unlock.` message.

#### `Observe: button1 button2...`
Enables observing on physical button, axis or pad. Works like Lock, but events from observed sources are processed normally and to client at same time.

Any number of clients can observe same source, so upon this requests, daemon always responds with `OK.`, as long as observing is enabled in configuration.
While source is observed, daemon keeps sending `Event: ...` messages every time when button is pressed, released, axis moved, etc...

Unlocking is done automatically when client is disconnected, or using `Unlock.` message.

#### `Replace: button actionstring`
Temporally replaces action set on physical button, axis or pad. This works in
same way as lock, so action is restored when client requesting change disconnects
or call `Unlock.`

If requested button (axis, pad) is already locked, daemon will respond with
`Fail: cannot lock <button>`. If action string (which can contain spaces)
cannot be parsed, daemon responds with `Fail: failed to parse: <more info>`.
If everything went well, daemon respnds with `OK.`

#### `Feedback: position amplitude`
Asks daemon to generate feedback effect. Position can be one of 'LEFT', 'RIGHT' or 'BOTH' and
amplitude is integer in range 0 to 32768 and controls power of generated effect.

Daemon responds with `OK.`

#### `OSD: text to display`
Asks daemon to display OSD message. No escaping or quoting is needed, everything after colon is displayed
as text.

If OSD cannot be used (for example because daemon runs without X server), daemon responds with `Fail: ....` message.
Otherwise daemon responds with `OK.`. Note that doesn't necessary mean that OSD is visible to user, only
that scc-daemon managed to send request to scc-osd-daemon.

#### `Profile: filename.sccprofile`
Asks daemon to load another profile. No escaping or quoting is needed, everything after colon is used as filename, only spaces and tabs are stripped.

If profile is sucessfully loaded, daemon responds with `OK.` to client that initiated loading and sends `Current profile: ...` message to all clients.

If loading fails, daemon responds with `Fail: ....` message where error with entire backtrace is sent. Backtrace is escaped to fit it on single line.

#### `Reconfigure.`
Asks daemon to reload configuration file (`~/.config/scc/config.json`).
Daemon reloads and reapplies all controller configs and sends `Reconfigured.`
message to all connected clients, what causes them to reload configuration
file as well.
Daemon responds with `OK.`

#### `Register: value`
Send by scc-osd-daemon and scc-autoswitch-daemon to register their client connections.
When sent with same value with two or more clients, daemon will automatically close former connection
before registering new one.
scc-osd-daemon sends `Register: osd`
scc-autoswitch-daemon `Register: autoswitch`
Daemon responds with `OK.`

#### `Rescan.`
Asks daemon to rescan for new devices. Drivers may re-read its configuration if needed.
Daemon responds with `OK.`

#### `Restart.`
Restarts daemon. This has same effect as calling "scc-daemon None restart", as that's exactly what
gets called. All clients are disconnected immediately, so there is no response.

#### `Selected: menu_id item_id`
Send by scc-osd-daemon when user chooses item from displayed menu.
If menu_id or item_id contains spaces or quotes, it should be escaped.
Daemon responds with `OK.`

#### `State.`
Asks daemon to sent current state of controller. Format of response is device-specific,
but should be useful enough for single-purpose script or debugging.

If observing is not enabled in configuration, daemon responds with `Fail: Sniffing disabled.`
If there is no active controller, daemon responds with `Fail: no controller connected`. 
Otherwise, daemon responds with `State: ...` message.

#### `Gestured: gesture_string`
Send by scc-osd-daemon, when user draws gesture. Sent only after requested
by `OSD: gesture`. If user gesture cannot be recognized or user cancels it,
'3|' (valid gesture string with no meaning) is reported.
Daemon responds with `OK.`

#### `Turnoff.`
Turns off all controllers.
Daemon responds with `OK.`

#### `Unlock.`
Unlocks everything locked with `Lock...` and `Observe...` messages sent by same client.
It is not possible to unlock only one input or only one type of lock.

This operation cannot fail (and does nothing if there is nothing to unlock), so daemon always responds with `OK.`
