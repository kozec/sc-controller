"""
hidparse - just enough code to parse HID report from hidraw descriptor.

Based on
  - Pythonic binding for linux's hidraw ioctls
	  (https://github.com/vpelletier/python-hidraw)
  - Winfred Lu's rd-parse.py
	  (http://winfred-lu.blogspot.sk/2014/02/usb-hid-report-descriptor-parser-in.html)

Licensed under GPL 2.0
"""
from scc.lib.hidparse_data import GlobalItem, MainItem, LocalItem, UsagePage
from scc.lib.hidparse_data import SensorPage, SensorSelector, LightSensor
from scc.lib.hidparse_data import GenericDesktopPage, page_to_enum
from scc.lib.hidparse_data import MotionSensor, OrientationSensor
from scc.lib.hidparse_data import ModifierI2a, HidSensorProperty
from scc.lib.hidparse_data import ItemType, ItemLength, ItemBase
from scc.lib.hidparse_data import SensorEvent, SensorDataField
from scc.lib.hidparse_data import Collection, Unit, UnitType
from scc.lib import ioctl_opt
from scc.lib import IntEnum
import ctypes, fcntl, collections, struct

# hid.h
_HID_MAX_DESCRIPTOR_SIZE = 4096

AXES = [
	GenericDesktopPage.X,
	GenericDesktopPage.Y,
	GenericDesktopPage.Z,
	GenericDesktopPage.Rx,
	GenericDesktopPage.Ry,
	GenericDesktopPage.Rz,
]

# hidraw.h
class _hidraw_report_descriptor(ctypes.Structure):
	_fields_ = [
		('size', ctypes.c_uint),
		('value', ctypes.c_ubyte * _HID_MAX_DESCRIPTOR_SIZE),
	]


class _hidraw_devinfo(ctypes.Structure):
	_fields_ = [
		('bustype', ctypes.c_uint),
		('vendor', ctypes.c_short),
		('product', ctypes.c_short),
	]


class BusType(IntEnum):
	USB = 0x03
	HIL = 0x04
	BLUETOOTH = 0x05
	VIRTUAL = 0x06


class ReservedItem(object):
	_CACHE = {}
	
	def __init__(self, value):
		self.value = value
	
	
	def __repr__(self):
		return "<Reserved ID 0x%x>" % (self.value,)
	
	__str__ = __repr__
	
	def __new__(cls, value):
		if value not in cls._CACHE:
			cls._CACHE[value] = object.__new__(cls, value)
		return cls._CACHE[value]


def enum_or_reserved(enum, value):
	try:
		return enum(value)
	except ValueError:
		return ReservedItem(value)


_HIDIOCGRDESCSIZE =	ioctl_opt.IOR(ord('H'), 0x01, ctypes.c_int)
_HIDIOCGRDESC =		ioctl_opt.IOR(ord('H'), 0x02, _hidraw_report_descriptor)
_HIDIOCGRAWINFO =	ioctl_opt.IOR(ord('H'), 0x03, _hidraw_devinfo)
#_HIDIOCGFEATURE =	lambda len : ioctl_opt.IORW(ord('H'), 0x07, len)
_HIDIOCGFEATURE = lambda len: ioctl_opt.IOC(
	ioctl_opt.IOC_WRITE|ioctl_opt.IOC_READ, ord('H'), 0x07, len)


def _ioctl(devfile, func, arg, mutate_flag=False):
	result = fcntl.ioctl(devfile, func, arg, mutate_flag)
	if result < 0:
		raise IOError(result)


def get_device_info(devfile):
	"""
	Returns tuple of (bustype, vendor_id, product_id), where bustype is
	instance of BusType enum.
	"""
	devinfo = _hidraw_devinfo()
	_ioctl(devfile, _HIDIOCGRAWINFO, devinfo, True)
	return (BusType(devinfo.bustype), devinfo.vendor, devinfo.product)


def get_raw_report_descriptor(devfile):
	"""
	Returns raw HID report descriptor as list of bytes.
	"""
	descriptor = _hidraw_report_descriptor()
	size = ctypes.c_uint()
	_ioctl(devfile, _HIDIOCGRDESCSIZE, size, True)
	descriptor.size = size
	_ioctl(devfile, _HIDIOCGRDESC, descriptor, True)
	return descriptor.value[:size.value]


# Convert items to unsigned char, short, or int
def _it2u(it):
	if len(it) == 2:	# unsigned char
		n = it[1]
	elif len(it) == 3:	# unsigned short
		n = int('{:02x}{:02x}'.format(it[2], it[1]), 16)
	elif len(it) == 5:	# unsigned int
		n = int('{:02x}{:02x}{:02x}{:02x}'.format(it[4], it[3], it[2], it[1]), 16)
	else:
		n = 0
	return n


# Convert items to signed char, short, or int
def _it2s(it):
	if len(it) == 2:					 # signed char
		n = it[1]
		if n & 0x80:
			n -= 0x100
	elif len(it) == 3:				   # signed short
		n = int('{:02x}{:02x}'.format(it[2], it[1]), 16)
		if n & 0x8000:
			n -= 0x10000
	elif len(it) == 5:				   # signed int
		n = int('{:02x}{:02x}{:02x}{:02x}'.format(it[4], it[3], it[2], it[1]), 16)
		if n & 0x80000000:
			n -= 0x100000000
	else:
		n = 0
	return n


def parse_item(it, page):
	if it[0] != 0xFE:					# normal item
		itag = it[0] & 0xF0
		itype = it[0] & 0xC
		isize = it[0] & 0x3
	else:								# long item
		isize = it[1]
		itag = it[3] * 256 + it[2]
		raise ValueError("Not implemented: long item!!")
	
	if itype == 0x00:					# main items
		item = enum_or_reserved(MainItem, itag)
		if item == MainItem.Collection:
			col_type = enum_or_reserved(Collection, it[1])
			return item, col_type
		elif item in (MainItem.Input, MainItem.Output, MainItem.Feature):
			return (item,
				ItemType.Constant if it[1] & 0x1 else ItemType.Data,
				ItemLength.Variable if it[1] & 0x2 else ItemLength.Array,
				ItemBase.Relative if it[1] & 0x4 else ItemBase.Absolute,
			)
		else:
			# EndCollection or reserved
			return item,
	elif itype == 0x04:					# global items
		item = enum_or_reserved(GlobalItem, itag)
		if item == GlobalItem.UsagePage:
			page = enum_or_reserved(UsagePage, _it2u(it))
			return item, page
		elif item == GlobalItem.UnitExponent:
			# exponent
			value = it[1] if it[1] < 8 else it[1] - 0x10
			return item, value
		elif item == GlobalItem.Unit:
			if it[1] == 0:
				return item, UnitType.NoUnit, None
			nibble = it[1] & 0x0F
			unit_type = enum_or_reserved(UnitType, nibble)
			if it[1] & 0xF0 != 0:
				return item, unit_type, Unit.Length
			if len(it) > 2:
				if it[2] & 0x0F: return item, unit_type, Unit.Mass
				if it[2] & 0xF0: return item, unit_type, Unit.Item
			if len(it) > 3:
				if it[3] & 0x0F: return item, unit_type, Unit.Temperature
				if it[3] & 0xF0: return item, unit_type, Unit.Current
			if len(it) > 4:
				if it[4] & 0x0F: return item, unit_type, Unit.LuminousIntensity
			return item, unit_type, ReservedItem(it[1])
		elif item in (GlobalItem.LogicalMaximum, GlobalItem.PhysicalMaximum):
			# unsigned values
			return item, _it2u(it)
		elif item in (GlobalItem.LogicalMinimum, GlobalItem.PhysicalMinimum,
					GlobalItem.ReportSize):
			# signed values
			return item, _it2s(it)
		elif item in (GlobalItem.ReportID, GlobalItem.ReportCount):
			return item, it[1]
		else:
			return item
	elif itype == 0x08:					# local items
		item = enum_or_reserved(LocalItem, itag)
		if item == LocalItem.Usage:
			if page is SensorPage and isize == 2:	# sensor page & usage size is 2
				mdf = (it[2] & 0xf0) >> 4
				if it[2] & 0xf == 0x02:
					return (item, enum_or_reserved(ModifierI2a, mdf),
							enum_or_reserved(SensorEvent, it[1]))
				elif it[2] & 0xf== 0x03:
					return (item, enum_or_reserved(ModifierI2a, mdf),
							enum_or_reserved(HidSensorProperty, it[1]))
				elif it[2] & 0xf== 0x04:
					if it[1] & 0xf0 == 0x50:
						return (item, enum_or_reserved(ModifierI2a, mdf),
								enum_or_reserved(MotionSensor, it[1]))
					elif it[1] & 0xf0 == 0x70 or it[1] & 0xf0 == 0x80:
						return (item, enum_or_reserved(ModifierI2a, mdf),
								enum_or_reserved(OrientationSensor, it[1]))
					elif it[1] & 0xf0 == 0xD0:
						return (item, enum_or_reserved(ModifierI2a, mdf),
								enum_or_reserved(LightSensor, it[1]))
				elif it[2] & 0xf== 0x05:
					return (item, enum_or_reserved(ModifierI2a, mdf),
							enum_or_reserved(SensorDataField, it[1]))
				elif it[2] & 0xf == 0x08:
					return (item, enum_or_reserved(ModifierI2a, mdf),
							enum_or_reserved(SensorSelector, it[1]))
			elif isize == 3:			 # 4 bytes (usage page: usage id)
				uid = it[2] * 256 + it[1]
				upg = it[4] * 256 + it[3]
				page = enum_or_reserved(hidparse_data.UsagePage, upg)
				try:
					return item, page(uid)
				except ValueError:
					return item, uid
				return item, page
			else:
				try:
					return item, page(it[1])
				except ValueError:
					return item, it[1]
		elif item in (LocalItem.UsageMinimum, LocalItem.UsageMaximum,
					LocalItem.DesignatorMinimum, LocalItem.DesignatorMaximum,
					LocalItem.StringMinimum, LocalItem.StringMaximum):
			return item, _it2s(it)
		else:
			return item
	else:
		return ReservedItem(itype)


def _split_hid_items(data):
	size = 0
	for i in range(len(data)):
		if size != 0:					# skip bytes for the previous item
			size -= 1
			continue
		size = data[i] & 0x3			 # 3 means 4 bytes
		if size == 3:
			size = 4
		if i == 0xFE:					# long item
			size = data[i+1]
		yield data[i:i+size+1]


def parse_report_descriptor(data, flat_list=False):
	"""
	Parses HID report descriptor to list of elements.
	
	If flat_list is set to True, only one list is returned.
	Otherwise, each collection is stored in its own nested list.
	"""
	rv, page = [], GenericDesktopPage
	stack, col = [], rv
	for it in _split_hid_items(data):
		item = parse_item(it, page)
		if not flat_list and item[0] is MainItem.Collection:
			item = [ item ]
			col.append(item)
			stack.append(col)
			col = item
		elif not flat_list and item[0] is MainItem.EndCollection:
			col.append(item)
			col, stack = stack[0], stack[:-1]
		elif item[0] is GlobalItem.UsagePage:
			page = item[1]
			if item[1] in page_to_enum:
				page = page_to_enum[item[1]]
			else:
				page = GenericDesktopPage
			col.append(item)
		else:
			col.append(item)
	
	return rv


def get_report_descriptor(devfile, flat_list=False):
	"""
	Returns parsed HID report descriptor as list of elements.
	
	If flat_list is set to True, only one list is returned.
	Otherwise, each collection is stored in its own nested list.
	"""
	data = get_raw_report_descriptor(devfile)
	return parse_report_descriptor(data, flat_list)


class Parser(object):
	
	def __init__(self, code, offset, count, size):
		self.code = code
		self.value = 0
		self.offset = offset
		self.byte_offset = offset / 8
		self.bit_offset = offset % 8
		self.count = count
		self.len = count * size
		if self.len > 64:
			raise ValueError("Too many bytes in value: %i" % (self.len, ))
		elif self.len > 32:
			self.byte_len = 8
			self.fmt = "<Q"
		elif self.len > 16:
			self.byte_len = 4
			self.fmt = "<I"
		elif self.len > 8:
			self.byte_len = 2
			self.fmt = "<H"
		else:
			self.byte_len = 1
			self.fmt = "<B"
		self.additional_bits = offset % 8
	
	
	def decode(self, data):
		self.value, = struct.unpack(self.fmt, data[self.byte_offset: self.byte_offset + self.byte_len])
		self.value >>= self.additional_bits

HIDPARSE_TYPE_AXIS = 1
HIDPARSE_TYPE_BUTTONS = 2


class HIDButtonParser(Parser):
	TYPE = HIDPARSE_TYPE_BUTTONS
	
	def __repr__(self):
		return "<HID Buttons @%s len %s value %s>" % (self.offset, self.len, self.value)


class HIDAxisParser(Parser):
	TYPE = HIDPARSE_TYPE_AXIS
	
	def __repr__(self):
		return "<HID Axis @%s len %s value %s>" % (self.offset, self.len, self.value)


def make_parsers(data):
	size, count = 1, 0
	kind = None
	offset = 0
	parsers = []
	axis_id, buttons_id = 0, 0
	for x in parse_report_descriptor(data, True):
		# print x
		if x[0] == GlobalItem.ReportSize:
			size = x[1]
		elif x[0] == GlobalItem.ReportCount:
			count = x[1]
		elif x[0] == LocalItem.Usage:
			kind = x[1]
		elif x[0] == MainItem.Input:
			if x[1] == ItemType.Constant:
				pass
			elif x[1] == ItemType.Data:
				if kind in AXES:
					for i in range(count):
						parsers.append(HIDAxisParser(axis_id, offset + size * i, 1, size))
						axis_id += 1
				else:
					parsers.append(HIDButtonParser(buttons_id, offset, count, size))
					buttons_id += count
			offset += size * count
	size = offset / 8
	if offset % 8 > 0: size += 1
	return size, parsers
