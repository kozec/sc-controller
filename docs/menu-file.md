SC-Controller menu file specification
----------------------------------------

Menu file contains json-encoded list with menu items (actions), submenus,
separators and menu generators.

### Menu Items

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

specifies menu with two items.

### Submenus

Submenu is reference to another menu file (submenu cannot be defined in same
file or profile file). When selected, another menu is loaded and drawn over
original menu.
Submenu is dict with `submenu` key, value of key is filename relative to
`~/.config/scc/menus` or `/usr/share/scc/default_menus/`, whichever exists, in
that order.
`name` key may be defined.

Example:

	[{
	  "submenu": "profiles.menu", 
	  "name": "All Profiles"
	}]

specifies menu with sumbmenu called "All Profiles" defined in *profiles.menu*

### Separators

Separator is empty space that splits menu into two or more logical blocks.
Name, if set, is displayed in different way from menu items. Separator is
defined by dict with `separator` key set to True.

### Menu Generators

Generator is something that generates menu items automatically. It is defined
by dict with `generator` key, where value is type of generator to use.

Example:

	[{
	  "generator": "profiles"
	}, {
	  "id": "item2", 
	  "action": "turnoff()", 
	  "name": "Turn controller OFF", 
	}]

specifies menu with list of all profiles, followed by one normal menu item.


### Available generators
Only one so far...

#### `profiles`
Generates menu item for each available profile. Selecting item will switch to represented profile.
