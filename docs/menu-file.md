SC-Controller menu file specification
----------------------------------------

Menu file contains json-encoded list with menu items (actions), separators and
menu generators.

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

