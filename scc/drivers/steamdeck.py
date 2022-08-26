#!/usr/bin/env python2
"""
SCC - Steam Deck Driver

Based on sc_by_cable and steamdeck.c

Deck uses slightly different packed format and so common handle_inpu is not used.

On top of that, deck will automatically enable lizard mode unless requested
to not do so periodically.
"""

from scc.lib import IntEnum
from scc.lib.usb1 import USBError
from scc.drivers.usb import USBDevice, register_hotplug_device
from scc.constants import STICK_PAD_MIN, STICK_PAD_MAX
from scc.constants import SCButtons, ControllerFlags
from sc_dongle import ControllerInput, SCController, SCPacketType
import struct, logging, ctypes


VENDOR_ID			= 0x28de
PRODUCT_ID			= 0x1205
ENDPOINT			= 3
CONTROLIDX			= 2
PACKET_SIZE			= 128
UNLIZARD_INTERVAL	= 100
# Basically, sticks on deck tend to return to non-zero position
STICK_DEADZONE		= 3000

log = logging.getLogger("deck")


class DeckInput(ctypes.Structure):
	_fields_ = [
		('type', ctypes.c_uint8),
		('_a1', ctypes.c_uint8 * 3),
		('seq', ctypes.c_uint32),
		('buttons', ctypes.c_uint64),
		('lpad_x', ctypes.c_int16),
		('lpad_y', ctypes.c_int16),
		('rpad_x', ctypes.c_int16),
		('rpad_y', ctypes.c_int16),
		
		('accel_x', ctypes.c_int16),
		('accel_y', ctypes.c_int16),
		('accel_z', ctypes.c_int16),
		('gpitch', ctypes.c_int16),
		('groll', ctypes.c_int16),
		('gyaw', ctypes.c_int16),
		('q1', ctypes.c_uint16),
		('q2', ctypes.c_uint16),
		('q3', ctypes.c_uint16),
		('q4', ctypes.c_uint16),
		
		('ltrig', ctypes.c_uint16),
		('rtrig', ctypes.c_uint16),
		('stick_x', ctypes.c_int16),
		('stick_y', ctypes.c_int16),
		('rstick_x', ctypes.c_int16),
		('rstick_y', ctypes.c_int16),
		
		# Values above are readed directly from deck
		# Values bellow are converted so mapper can understand them
		('dpad_x', ctypes.c_int16),
		('dpad_y', ctypes.c_int16),
	]


class DeckButton(IntEnum):
	DOTS				= 0b100000000000000000000000000000000000000000000000000
	RSTICKTOUCH			= 0b000100000000000000000000000000000000000000000000000
	LSTICKTOUCH			= 0b000010000000000000000000000000000000000000000000000
	RGRIP2				= 0b000000001000000000000000000000000000000000000000000
	LGRIP2				= 0b000000000100000000000000000000000000000000000000000
	RSTICKPRESS			= 0b000000000000000000000000100000000000000000000000000
	LSTICKPRESS			= 0b000000000000000000000000000010000000000000000000000
	# bit 21 unused?
	RPADTOUCH			= 0b000000000000000000000000000000100000000000000000000
	LPADTOUCH			= 0b000000000000000000000000000000010000000000000000000
	RPADPRESS			= 0b000000000000000000000000000000001000000000000000000
	LPADPRESS			= 0b000000000000000000000000000000000100000000000000000
	RGRIP				= 0b000000000000000000000000000000000010000000000000000
	LGRIP				= 0b000000000000000000000000000000000001000000000000000
	START				= 0b000000000000000000000000000000000000100000000000000
	C					= 0b000000000000000000000000000000000000010000000000000
	BACK				= 0b000000000000000000000000000000000000001000000000000
	DPAD_DOWN			= 0b000000000000000000000000000000000000000100000000000
	DPAD_LEFT			= 0b000000000000000000000000000000000000000010000000000
	DPAD_RIGHT			= 0b000000000000000000000000000000000000000001000000000
	DPAD_UP				= 0b000000000000000000000000000000000000000000100000000
	A					= 0b000000000000000000000000000000000000000000010000000
	X					= 0b000000000000000000000000000000000000000000001000000
	B					= 0b000000000000000000000000000000000000000000000100000
	Y					= 0b000000000000000000000000000000000000000000000010000
	LB					= 0b000000000000000000000000000000000000000000000001000
	RB					= 0b000000000000000000000000000000000000000000000000100
	LT					= 0b000000000000000000000000000000000000000000000000010
	RT					= 0b000000000000000000000000000000000000000000000000001


DIRECTLY_TRANSLATABLE_BUTTONS = (0
	| DeckButton.A | DeckButton.B | DeckButton.X | DeckButton.Y
	| DeckButton.LB | DeckButton.RB | DeckButton.LT | DeckButton.RT
	| DeckButton.START | DeckButton.C | DeckButton.BACK
	| DeckButton.RGRIP | DeckButton.LGRIP
	| DeckButton.RPADTOUCH | DeckButton.LPADTOUCH
	| DeckButton.RPADPRESS | DeckButton.LPADPRESS
);


def map_button(i, from_, to):
	return to if (i.buttons & from_) else 0


def map_dpad(i, low, hi):
	if (i.buttons & low) != 0:
		return STICK_PAD_MIN
	elif (i.buttons & hi) != 0:
		return STICK_PAD_MAX
	else:
		return 0


def apply_deadzone(value, deadzone):
	if value > -deadzone and value < deadzone:
		return 0
	return value


class Deck(USBDevice, SCController):
	flags = ( 0
		| ControllerFlags.SEPARATE_STICK
		| ControllerFlags.HAS_DPAD
		| ControllerFlags.IS_DECK
	)
	
	def __init__(self, device, handle, daemon):
		self.daemon = daemon
		USBDevice.__init__(self, device, handle)
		SCController.__init__(self, self, CONTROLIDX, ENDPOINT)
		self._old_state = DeckInput()
		self._input = DeckInput()
		self._ready = False
		
		self.claim_by(klass=3, subclass=0, protocol=0)
		self.read_serial()
	
	def generate_serial(self):
		self._serial = "%s:%s" % (self.device.getBusNumber(), self.device.getPortNumber())
	
	def disconnected(self):
		# Overrided to skip returning serial# to pool.
		pass
	
	def set_gyro_enabled(self, enabled):
		# Always on on deck
		pass
	
	def get_gyro_enabled(self):
		# Always on on deck
		return True
	
	def get_type(self):
		return "deck"
	
	def __repr__(self):
		return "<Deck %s>" % (self.get_id(),)
	
	def get_gui_config_file(self):
		return "deck.config.json"
	
	def configure(self, idle_timeout=None, enable_gyros=None, led_level=None):
		FORMAT = b'>BBBB60x'
		# Timeout & Gyros
		self._driver.overwrite_control(self._ccidx, struct.pack(
			FORMAT, SCPacketType.CONFIGURE, 0x03, 0x08, 0x07))
	
	def clear_mappings(self):
		FORMAT = b'>BB62x'
		# Timeout & Gyros
		self._driver.overwrite_control(self._ccidx,
			struct.pack(FORMAT, SCPacketType.CLEAR_MAPPINGS, 0x01))
	
	def on_serial_got(self):
		log.debug("Got SteamDeck with serial %s", self._serial)
		self._id = "deck%s" % (self._serial,)
		self.set_input_interrupt(ENDPOINT, 64, self._on_input)	
	
	def _on_input(self, endpoint, data):
		if not self._ready:
			self.daemon.add_controller(self)
			self.configure()
			self._ready = True
		
		self._old_state, self._input = self._input, self._old_state
		ctypes.memmove(ctypes.addressof(self._input), data, len(data))
		if self._input.seq % UNLIZARD_INTERVAL == 0:
			# Keeps lizard mode from happening
			self.clear_mappings()
		
		# Handle dpad
		self._input.dpad_x = map_dpad(self._input, DeckButton.DPAD_LEFT, DeckButton.DPAD_RIGHT)
		self._input.dpad_y = map_dpad(self._input, DeckButton.DPAD_DOWN, DeckButton.DPAD_UP)
		# Convert buttons
		self._input.buttons = (0
			| ((self._input.buttons & DIRECTLY_TRANSLATABLE_BUTTONS) << 8)
			| map_button(self._input, DeckButton.DOTS, SCButtons.DOTS)
			# | map_button(self._input, DeckButton.RSTICKTOUCH, ....)	// not mapped
			# | map_button(self._input, DeckButton.LSTICKTOUCH, ....) // not mapped
			| map_button(self._input, DeckButton.LSTICKPRESS, SCButtons.STICKPRESS)
			| map_button(self._input, DeckButton.RSTICKPRESS, SCButtons.RSTICKPRESS)
			| map_button(self._input, DeckButton.LGRIP2, SCButtons.LGRIP2)
			| map_button(self._input, DeckButton.RGRIP2, SCButtons.RGRIP2)
		)
		# Convert triggers
		self._input.ltrig >>= 7
		self._input.rtrig >>= 7
		# Apply deadzones
		self._input.stick_x = apply_deadzone(self._input.stick_x, STICK_DEADZONE)
		self._input.stick_y = apply_deadzone(self._input.stick_y, STICK_DEADZONE)
		self._input.rstick_x = apply_deadzone(self._input.rstick_x, STICK_DEADZONE)
		self._input.rstick_y = apply_deadzone(self._input.rstick_y, STICK_DEADZONE)
		
		m = self.get_mapper()
		if m:
			self.mapper.input(self, self._old_state, self._input)
	
	def close(self):
		if self._ready:
			self.daemon.remove_controller(self)
			self._ready = False
		USBDevice.close(self)
	
	def turnoff(self):
		log.warning("Ignoring request to turn off steamdeck.")


def init(daemon, config):
	""" Registers hotplug callback for controller dongle """
	def cb(device, handle):
		return Deck(device, handle, daemon)
	
	register_hotplug_device(cb, VENDOR_ID, PRODUCT_ID)
	return True

