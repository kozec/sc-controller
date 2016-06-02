SC-Controller menu file specification
----------------------------------------

Menu file contains json-encoded list with menu items - actions.

Every menu item is defined by action, in same way  as action would be defined
[in profile file](profile-file.md#Action_definition) with one additional
`id` key. `id` specifies action ID and can be anything, but each menu item
should have unique ID.

`name` key is still optional, but highly recommended as used as menu item title
displayed on screen. If `name` is not specified, title is auto-generated.

Example:

	[{
	  "id": "item1", 
	  "action": "profile('Desktop')", 
	  "name": "Switch to Desktop profile", 
	}, {
	  "id": "item2", 
	  "action": "turnoff()", 
	  "name": "Turn controller OFF", 
	}]

Specifies menu with two items.