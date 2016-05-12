To control running daemon instance, unix socket in user directory is used.
Controlling protocol uses case-sensitive messages terminated by newline. Message type and message arguments are delimited by `:`.

When new connection is accepted, daemon sends some info:

```
SCCDaemon
Version: 0.1
PID: 123456
Current profile: filename.sccprofile
Ready.
```

Connection is then held until client side closes it.


# Messages sends by daemon:

#### `Current profile: filename.sccprofile`
Sent to every client when profile file is loaded and used. Automatically sent when connnection is accepted and when profile is changed.

#### `Error: description`
Sent to every client when error is detected. May be sent repeadedly, until error condition is cleared.
After that, `Ready.` is sent to indicate that emulation works again.

#### `Fail: text`
Indicates error client that sent request.

#### `OK.`
Indicates sucess to client that sent request.

#### `PID: xyz`
Reports PID of *scc-daemon* instance. Automatically sent when connnection is accepted.

#### `Ready.`
Automatically sent when connnection is accepted to indicate that there is no error and daemon is working as expected.

#### `SCCDaemon`
Just identification message, automatically sent when connnection is accepted.
Can be either ignored or used to check if remote side really is *scc-daemon*.

#### `Version: x.y`
Identifies daemon version. Automatically sent when connnection is accepted.

# Commands sent from client to daemon

#### `Profile: filename.sccprofile`
Asks daemon to load another profile. No escaping or quouting is needed, everything after colon is used as filename, only spaces and tabs are stripped.

If profile is sucessfully loaded, daemon responds with `OK.` to client that initiated loading and sends `Current profile: ...` message to all clients.

If loading fails, daemon responds with `Fail: ....` message where error with entire backtrace is sent. Backtrace is escaped to fit it on single line.
