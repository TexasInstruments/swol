"""Send wireshark data to wireshark"""

import enum
import struct
from collections import OrderedDict, namedtuple
import logging
import pyuv
from .wlogger_plugin import *

logger = logging.getLogger('wireshark_output')

class WSOutputElement(namedtuple('output_element', "protofield value custom_val",
                                 defaults=(None, None, None))):
    """Element to build list of wireshark output"""

    @classmethod
    def from_defaults(cls, protofield, value=None, custom_val=None):
        """
        Element to build list of wireshark output

        protofield: one of Protofields
        value: value corresponding to protofield, one of Types
        custom_val: the value of the custom protofield, of type custom_type
        """
        return cls(protofield, value, custom_val)


##########################################################################################

class Protofields(enum.Enum):
    """Protofield indices TODO: are these used by the dissector?"""
    SWO_RAT_S = 0
    SWO_RTC_S = 1
    SWO_RAT_T = 2
    SWO_OPCODE = 3
    SWO_MODULE = 4
    SWO_LEVEL = 5
    SWO_FILE = 6
    SWO_LINE = 7
    SWO_INFO = 8
    SWO_EVENT = 9
    BLE_OPCODE = 20
    BLE_LAYER = 21
    BLE_EVENT = 22
    BLE_HANDLE = 23
    BLE_STATUS = 24
    BLE_INFO = 25
    BLE_LL_TASK = 26
    DRIVER_FILE = 60
    DRIVER_STATUS = 61
    DRIVER_POWER_CONSTRAINT = 62
    RF_OPCODE = 70
    TIRTOS_LOG_EVENT = 80
    TIRTOS_LOG_FILE = 81
    TIRTOS_LOG_LINE = 82
    COMMON_CUSTOM = 230
    COMMON_PROTOCOL = 231
    COMMON_INFO = 232
    COMMON_OPEN_TREE = 233
    COMMON_CLOSE_TREE = 234


# These strings must exactly match the strings defined in the wlogger_disector.lua
PROTO_FIELD_ID_TO_STRING = {
    Protofields.SWO_RAT_S: "Radio Time Secs",
    Protofields.SWO_RTC_S: "Real Time Clock",
    Protofields.SWO_RAT_T: "Radio Time Ticks",
    Protofields.SWO_OPCODE: "SWO opcode",
    Protofields.SWO_MODULE: "SWO module",
    Protofields.SWO_LEVEL: "SWO level",
    Protofields.SWO_FILE: "SWO file",
    Protofields.SWO_LINE: "SWO line",
    Protofields.SWO_INFO: "SWO info",
    Protofields.SWO_EVENT: "SWO event",
    Protofields.BLE_OPCODE: "BLE OpCode",
    Protofields.BLE_LAYER: "BLE Layer",
    Protofields.BLE_EVENT: "BLE Event",
    Protofields.BLE_HANDLE: "BLE Conn/adv handle",
    Protofields.BLE_STATUS: "BLE Status",
    Protofields.BLE_INFO: "BLE Info",
    Protofields.BLE_LL_TASK: "BLE LL Task",
    Protofields.RF_OPCODE: "RF OpCode",
    Protofields.DRIVER_FILE: "Driver",
    Protofields.DRIVER_STATUS: "Driver status",
    Protofields.DRIVER_POWER_CONSTRAINT: "Power constraint",
    Protofields.TIRTOS_LOG_EVENT: "Log Event",
    Protofields.TIRTOS_LOG_FILE: "File",
    Protofields.TIRTOS_LOG_LINE: "Line",
    Protofields.COMMON_CUSTOM: "",
    Protofields.COMMON_PROTOCOL: "Stream ID",
    Protofields.COMMON_INFO: "Message",
    Protofields.COMMON_OPEN_TREE: "ADD_LEVEL",
    Protofields.COMMON_CLOSE_TREE: "END_ADD_LEVEL",
}

##########################################################################################
# Gandelf Functionality

loop = pyuv.Loop.default_loop()
pipe = pyuv.Pipe(loop, True)


def pipe_on_connect(error):
    if error is not None:
        raise pyuv.error.PipeError(pyuv.errno.strerror(error))
    logger.info('Pipe connected')


def pipe_open(pipe_name):
    logger.info('Connecting to pipe')
    pipe.connect(pipe_name, pipe_on_connect)
    loop.run()


def pipe_close():
    logger.info("Closing pipe")
    pipe.close()


def pipe_send_data(buf):
    pipe.write(buf)
    loop.run()


def gandelf_send_message(stream_id, msg):
    """
    Send a string to wireshark for output

    Args:
        stream_id: identifier for packet in wireshark output
        msg: string to send

    """
    data = [
        WSOutputElement(Protofields.COMMON_OPEN_TREE, "General"),
        WSOutputElement(Protofields.COMMON_PROTOCOL, stream_id),
        WSOutputElement(Protofields.COMMON_INFO, str(msg)),
        WSOutputElement(Protofields.COMMON_CLOSE_TREE)
    ]

    gandelf_send_data(stream_id, data)


def gandelf_send_data(stream_id, frame):
    """
    Send data to wireshark to be parsed into protofields

    Args:
      frame: list of WSOutputElement
      stream_id: identifier on wireshark output of logger's stream
    """

    # TODO: send stream_id

    # string => length:value
    def lv(s):
        return struct.pack('<L', len(s)) + s.encode()

    data = bytes()
    for x in frame:
        protofield = PROTO_FIELD_ID_TO_STRING[x.protofield]
        if x.protofield is Protofields.COMMON_CUSTOM:
            value = "{}: {}".format(x.value, x.custom_val)
        else:
            value = x.value
        if value is None:
            value = '\x42'

        if value != '':
            data += lv(protofield)
            data += lv(str(value))

    pipe_send_data(data)


##########################################################################################
# Wlogger Functionality

def wlogger_send_message(stream_id, msg):
    """
    Send a string to wireshark for output

    Args:
        stream_id: identifier for packet in wireshark output
        msg: string to send

    """
    data = OrderedDict()
    data["General"] = OrderedDict()
    data["General"]["Stream ID"] = stream_id
    data["General"]["Message"] = "{}".format(msg)

    send_data(data)


def wlogger_get_leaf(data, group_name_stack):
    """
    Helper function to build wireshark data output

    Args:
      data: input data
      group_name_stack: current tree

    Returns:
        Leaf to build data into

    """
    ret = data
    for group_name in group_name_stack:
        if group_name not in ret.keys():
            ret[group_name] = OrderedDict()

        ret = ret[group_name]
    return ret


def wlogger_send_data(stream_id, frame):
    """
    Send data to wireshark to be parsed into protofields

    Args:
      frame: list of WSOutputElement
      stream_id: identifier on wireshark output of logger's stream

    """
    data = OrderedDict()
    data["General"] = OrderedDict()
    data["General"]["Stream ID"] = stream_id

    group_name_stack = []
    leaf = None

    for x in frame:
        if x.protofield == Protofields.COMMON_OPEN_TREE:
            group_name_stack.append(x.value)
            leaf = wlogger_get_leaf(data, group_name_stack)

        elif x.protofield == Protofields.COMMON_CLOSE_TREE:
            if len(group_name_stack) > 0:
                group_name_stack.pop()
            leaf = wlogger_get_leaf(data, group_name_stack)

        elif x.protofield == Protofields.COMMON_INFO:
            data["General"]["Message"] = "{}".format(x.value)

        elif x.protofield == Protofields.COMMON_CUSTOM:
            leaf[x.value] = "{}".format(x.custom_val)

        else:
            if x.protofield is not None and x.value is not None:
                leaf[PROTO_FIELD_ID_TO_STRING[x.protofield]] = "{}".format(x.value)

    send_data(data)
