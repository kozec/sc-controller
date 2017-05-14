# -*- coding: utf-8 -*-
"""
Other helper functions.
"""
from __future__ import absolute_import

from . import usage_pages, helpers, winapi
from operator import attrgetter

def write_documentation(self, output_file):
    "Issue documentation report on output_file file like object"
    if not self.is_opened():
        raise helpers.HIDError("Device has to be opened to get documentation")
    #format
    class CompundVarDict(object):
        """Compound variables dictionary.
        Keys are strings mapping variables.
        If any string has a '.' on it, it means that is an
        object with an attribute. The attribute name will be
        used then as the returned item value.
        """
        def __init__(self, parent):
            self.parent = parent
        def __getitem__(self, key):
            if '.' not in key:
                return self.parent[key]
            else:
                all_keys = key.split('.')
                curr_var = self.parent[all_keys[0]]
                for item in all_keys[1:]:
                    new_var = getattr(curr_var, item)
                    curr_var = new_var
                return new_var
    dev_vars = vars(self)
    dev_vars['main_usage_str'] = repr(
            usage_pages.HidUsage(self.hid_caps.usage_page,
                self.hid_caps.usage) )
    output_file.write( """\n\
HID device documentation report
===============================

Top Level Details
-----------------

Manufacturer String:    %(vendor_name)s
Product Sting:          %(product_name)s
Serial Number:          %(serial_number)s

Vendor ID:              0x%(vendor_id)04x
Product ID:             0x%(product_id)04x
Version number:         0x%(version_number)04x

Device Path:            %(device_path)s
Device Instance Id:     %(instance_id)s
Parent Instance Id:     %(parent_instance_id)s

Top level usage:        Page=0x%(hid_caps.usage_page)04x, Usage=0x%(hid_caps.usage)02x
Usage identification:   %(main_usage_str)s
Link collections:       %(hid_caps.number_link_collection_nodes)d collection(s)

Reports
-------

Input Report
~~~~~~~~~~~~
Length:     %(hid_caps.input_report_byte_length)d byte(s)
Buttons:    %(hid_caps.number_input_button_caps)d button(s)
Values:     %(hid_caps.number_input_value_caps)d value(s)

Output Report
~~~~~~~~~~~~~
length:     %(hid_caps.output_report_byte_length)d byte(s)
Buttons:    %(hid_caps.number_output_button_caps)d button(s)
Values:     %(hid_caps.number_output_value_caps)d value(s)

Feature Report
~~~~~~~~~~~~~
Length:     %(hid_caps.feature_report_byte_length)d byte(s)
Buttons:    %(hid_caps.number_feature_button_caps)d button(s)
Values:     %(hid_caps.number_feature_value_caps)d value(s)

""" % CompundVarDict(dev_vars)) #better than vars()!
    #return
    # inspect caps
    for report_kind in [winapi.HidP_Input,
            winapi.HidP_Output, winapi.HidP_Feature]:
        all_usages = self.usages_storage.get(report_kind, [])
        if all_usages:
            output_file.write('*** %s Caps ***\n\n' % {
                    winapi.HidP_Input   : "Input",
                    winapi.HidP_Output  : "Output",
                    winapi.HidP_Feature : "Feature"
                    }[report_kind])
            # normalize usages to allow sorting by usage or min range value
            for item in all_usages:
                if getattr(item, 'usage', None) != None:
                    item.flat_id = item.usage
                elif getattr(item, 'usage_min', None) != None:
                    item.flat_id = item.usage_min
                else:
                    item.flat_id = None
            sorted(all_usages, key=attrgetter('usage_page', 'flat_id'))
            for usage_item in all_usages:
                # remove helper attribute
                del usage_item.flat_id

                all_items = usage_item.inspect()
                # sort first by 'usage_page'...
                usage_page = all_items["usage_page"]
                del all_items["usage_page"]
                if "usage" in all_items:
                    usage = all_items["usage"]
                    output_file.write("    Usage {0} ({0:#x}), "\
                            "Page {1:#x}\n".format(usage, usage_page))
                    output_file.write("    ({0})\n".format(
                        repr(usage_pages.HidUsage(usage_page, usage))) )
                    del all_items["usage"]
                elif 'usage_min' in all_items:
                    usage = (all_items["usage_min"], all_items["usage_max"])
                    output_file.write("    Usage Range {0}~{1} ({0:#x}~{1:#x}),"
                            " Page {2:#x} ({3})\n".format(
                                usage[0], usage[1], usage_page,
                                str(usage_pages.UsagePage(usage_page))) )
                    del all_items["usage_min"]
                    del all_items["usage_max"]
                else:
                    raise AttributeError("Expecting any usage id")
                attribs = list( all_items.keys() )
                attribs.sort()
                for key in attribs:
                    if 'usage' in key:
                        output_file.write("{0}{1}: {2} ({2:#x})\n".format(' '*8,
                            key, all_items[key]))
                    else:
                        output_file.write("{0}{1}: {2}\n".format(' '*8,
                            key, all_items[key]))
                output_file.write('\n')

