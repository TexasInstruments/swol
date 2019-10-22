import sys
import os
import enum
from dataclasses import *
from swo.swo_framer import *
from wireshark_output.wireshark_output import *
from modules.ble.ble_constants import *
import struct
from construct import *
import logging

logger = logging.getLogger("BLE Framer")

layer_str_to_events = {
    "LL": LLEventIds,
    "GAP": GAPEventIds,
    "SM": SMEventIds,
    "GAPBondMgr": GapBondMgrEventIds,
    "OSAL Callback Timer": OsalCbEventIds
}


class BLEOpcode(enum.Enum):
    """Opcodes of BLE Frames"""
    OSAL_EVENT = 0
    OSAL_MSG = 1
    LL_SCHED_EVT = 2


@dataclass
class BLEEvent(FrameBase):
    """
    BLE Event frame. This will be subclassed by all other BLE frames

    Args:
        swo_frame: input SWOFrame
        wireshark_out: list of WSOutputElements describing wireshark output

    """
    swo_frame: SWOFrame = None
    wireshark_out: list = None

    def __post_init__(self):
        """Store input SWO frame information as part of BLE frame. Also start building wireshark output"""
        self.rat_ts_s = self.swo_frame.rat_ts_s
        self.rtc_ts_s = self.swo_frame.rtc_ts_s
        self.opcode = self.swo_frame.opcode
        self.file = self.swo_frame.file
        self.line = self.swo_frame.line
        self.level = self.swo_frame.level
        self.module = self.swo_frame.module
        # Append open tree after SWO output
        self.wireshark_out = self.swo_frame.wireshark_out + [
            WSOutputElement(Protofields.COMMON_OPEN_TREE, "BLE Logger Frame")]

    def __str__(self):
        return "RAT: %f s, RTC: %f : %s --> " % (self.rat_ts_s, self.rtc_ts_s, self.ble_opcode.name)


@dataclass
class OSALEvent(BLEEvent):
    """
    OSAL Event Frame.

    Args:
        ble_opcode: opcode describing this ble frame
        layer_map: dictionary of layer values to strings

    """
    ble_opcode: BLEOpcode = BLEOpcode.OSAL_EVENT
    layer_map: dict = field(default_factory=dict)

    def __post_init__(self):
        """Parse SWO Event frame into OSAL Event frame. Also do common wireshark output building."""
        super().__post_init__()
        self.layer_int = self.swo_frame.values[0]
        try:
            self.layer_str = self.layer_map[self.layer_int]
        except KeyError:  # Asssume callback timer is only task not accounted for
            self.layer_str = "OSAL Callback Timer"
        finally:
            self.event = layer_str_to_events[self.layer_str](self.swo_frame.values[1])
        # Build wireshark output
        self.wireshark_out += [WSOutputElement(Protofields.BLE_OPCODE, self.ble_opcode.name),
                               WSOutputElement(Protofields.BLE_LAYER, self.layer_str),
                               WSOutputElement(Protofields.BLE_EVENT, self.event.name)]

    def __str__(self):
        return "%s received in %s" % (self.event.name, self.layer_str)


@dataclass
class OSALMsg(BLEEvent):
    """
    OSAL Message Frame. This will be subclassed by all OSAL messages

    Args:
        ble_opcode: opcode describing this ble frame
        layer_map: dictionary of layer values to strings

    """
    ble_opcode: BLEOpcode = BLEOpcode.OSAL_MSG
    layer_map: dict = field(default_factory=dict)

    def __post_init__(self):
        """Extract common OSAL Message information: layer, event. Also do common wireshark output building."""
        super().__post_init__()
        self.buf = self.swo_frame.events[0].buf
        # First byte is task id (layer)
        self.layer_int = self.buf[0]
        self.layer_str = self.layer_map[self.layer_int]
        # Next byte is event type
        self.event = OSALMsgs(self.buf[1])
        # Build wireshark output
        self.wireshark_out += [WSOutputElement(Protofields.BLE_OPCODE, self.ble_opcode.name),
                               WSOutputElement(Protofields.BLE_LAYER, self.layer_str),
                               WSOutputElement(Protofields.BLE_EVENT, self.event.name)]

    def __str__(self):
        return "%s received in %s: " % (self.event.name, self.layer_str)


# def get_status(val)
#     try:
#         stat_str = Statuses(val).name
#     except ValueError:
#         stat_str =

@dataclass
class GAPOsalMessage(OSALMsg):
    """GAP OSAL Message Frame."""
    conn_handle = None

    def __post_init__(self):
        """Find GAP event, status, and continue building wireshark output"""
        super().__post_init__()
        self.gap_event = GAPMsgs(self.buf[3])
        try:
            self.status = Statuses(self.buf[2])
        except ValueError:
            self.status = Statuses.ERROR
        # Build wireshark output
        self.wireshark_out += [WSOutputElement(Protofields.BLE_STATUS, self.status.name)]
        self.wireshark_out += [WSOutputElement(Protofields.COMMON_OPEN_TREE, self.gap_event.name)]
        for x in self.swo_frame.events[1:]:
            self.wireshark_out += [WSOutputElement(Protofields.COMMON_CUSTOM, x.string,
                                                   ":".join(reversed(["{:0>2X}".format(i) for i in x.buf])))]
            if x.string.lower() == "connection handle": self.conn_handle = Int16ul.parse(bytes(x.buf))
        self.wireshark_out += [WSOutputElement(Protofields.COMMON_CLOSE_TREE)]
        if self.conn_handle is not None: self.wireshark_out += [
            WSOutputElement(Protofields.BLE_HANDLE, self.conn_handle)]

    def __str__(self):
        return "%s with status %s" % (self.gap_event.name, self.status.name)


@dataclass
class L2CAPDataInMsg(OSALMsg):
    """Frame displaying all incoming data passed through L2CAP (ATT or SM)"""

    def __post_init__(self):
        """Find connection handle, method, and parse payload based on layer and method"""
        super().__post_init__()
        self.conn_handle = struct.unpack("<H", bytes(self.buf[4:6]))[0]
        self.payload = bytes(self.swo_frame.events[1].buf)
        self.container = None
        try:
            self.status = Statuses(self.buf[2])
        except ValueError:
            self.status = Statuses.ERROR
        self.method = GATTDataMsgs(self.payload[0]) if self.layer_str == "GATT" else SMDataMsgs(self.payload[0])
        parser = att_payload_parsing if self.layer_str == "GATT" else sm_payload_parsing
        self.wireshark_out += [WSOutputElement(Protofields.BLE_STATUS, self.status.name),
                               WSOutputElement(Protofields.BLE_HANDLE, self.conn_handle),
                               WSOutputElement(Protofields.COMMON_OPEN_TREE, self.method.name)]
        try:
            self.container = parser[self.method].parse(self.payload[1:])
            for k, v in self.container.items():
                if k is not "_io":
                    self.wireshark_out += [WSOutputElement(Protofields.COMMON_CUSTOM, k, str(v))]
        except KeyError:
            # Not all packets need to be parsed
            pass
            # Build wireshark output
            self.wireshark_out += [WSOutputElement(Protofields.COMMON_CLOSE_TREE)]

    def __str__(self):
        return "%s received on handle %d with status %s" % (self.method.name, self.conn_handle, self.status.name)


@dataclass
class L2CAPDataOutMsg(OSALMsg):
    """Frame displaying all outgoing data passed through L2CAP (ATT or SM)"""

    def __post_init__(self):
        """Find connection handle, method, and parse payload based on layer and method and continue building wireshark output"""
        super().__post_init__()
        self.conn_handle = struct.unpack("<H", bytes(self.buf[3:5]))[0]
        self.payload = bytes(self.swo_frame.events[1].buf)
        self.container = None
        self.method = GATTDataMsgs(self.payload[0]) if self.layer_str == "GATT" else SMDataMsgs(self.payload[0])
        parser = att_payload_parsing if self.layer_str == "GATT" else sm_payload_parsing
        self.wireshark_out += [WSOutputElement(Protofields.BLE_HANDLE, self.conn_handle),
                               WSOutputElement(Protofields.COMMON_OPEN_TREE, self.method.name)]
        try:
            self.container = parser[self.method].parse(self.payload[1:])
            for k, v in self.container.items():
                if k is not "_io":
                    self.wireshark_out += [WSOutputElement(Protofields.COMMON_CUSTOM, k, str(v))]
        except KeyError:
            # Not all packets need to be parsed
            pass
        # Build wireshark output
        self.wireshark_out += [WSOutputElement(Protofields.COMMON_CLOSE_TREE)]

    def __str__(self):
        return "%s sending to handle %d" % (self.method.name, self.conn_handle)


@dataclass
class HCIGapEventMsg(OSALMsg):
    """Not parsed yet"""

    def __post_init__(self):
        """Not parsed yet"""
        super().__post_init__()
        logger.warning("new event: ")


@dataclass
class HCIEventMsg(OSALMsg):
    """HCI Event Message Frame"""

    def __post_init__(self):
        """Extract HCI event and status. Continue building wireshark output"""
        super().__post_init__()
        self.hci_event = HCIEventMsgs(self.buf[3])
        try:
            self.status = Statuses(self.buf[4])
        except ValueError:
            self.status = Statuses.ERROR
        self.wireshark_out += [WSOutputElement(Protofields.BLE_STATUS, self.status.name)]

    def __str__(self):
        return "with status %s --> %s" % (self.status.name, self.hci_event.name)


@dataclass
class GATTDataMsg(OSALMsg):
    """Data message at GATT layer"""

    def __post_init__(self):
        """Extract status, connection, handle, and method. Continue building wireshark output."""
        super().__post_init__()
        try:
            self.status = Statuses(self.buf[2])
        except ValueError:
            self.status = Statuses.ERROR
        self.conn_handle = struct.unpack("<H", bytes(self.buf[3:5]))[0]
        self.method = GATTDataMsgs(self.buf[5])
        self.wireshark_out += [WSOutputElement(Protofields.BLE_STATUS, self.status.name),
                               WSOutputElement(Protofields.BLE_HANDLE, self.conn_handle)]

    def __str__(self):
        return "%s received on handle %d with status %s" % (self.method.name, self.conn_handle, self.status.name)


@dataclass
class EventEventMsg(OSALMsg):
    """Message describing an HCI event sent as a GAP event"""

    def __post_init__(self):
        """Extract status, GAP event, subtype (secondary event), and continue building wireshark output."""
        super().__post_init__()
        self.gap_event = HCIGAPMsgs(self.buf[2])
        self.status = None
        self.subtype = None
        if self.gap_event == HCIGAPMsgs.HCI_COMMAND_COMPLETE_EVENT_CODE or self.gap_event == HCIGAPMsgs.HCI_VE_EVENT_CODE:
            self.subtype = HCICmdOpcodes(struct.unpack("<H", bytes(self.buf[5:7]))[0])
        elif self.gap_event == HCIGAPMsgs.HCI_LE_EVENT_CODE:
            self.subtype = HCIEventOpcodes(self.buf[3])
        elif self.gap_event == HCIGAPMsgs.HCI_COMMAND_STATUS_EVENT_CODE:
            try:
                self.status = Statuses(self.buf[3])
            except ValueError:
                self.status = Statuses.ERROR
            self.subtype = HCICmdOpcodes(struct.unpack("<H", bytes(self.buf[5:7]))[0])
            self.wireshark_out += [WSOutputElement(Protofields.BLE_STATUS, self.status.name)]

    def __str__(self):
        string = self.gap_event.name
        if self.subtype is not None:
            string += " of " + self.subtype.name
        if self.status is not None:
            string += " with status " + self.status.name
        return string


@dataclass
class ControllerToHostEventMsg(OSALMsg):
    """
    Controller to host Message

    """

    def __post_init__(self):
        """Extract packet type and continue building wireshark output"""
        super().__post_init__()

    def __str__(self):
        return "Controller to host packet"


@dataclass
class HCIDataEventMsg(OSALMsg):
    """
    HCI Data Event Message

    Args:
        conn_handle: connection handle regarding message

    """
    conn_handle: int = None

    def __post_init__(self):
        """Extract GAP event, connection handle, and continue building wireshark output"""
        super().__post_init__()
        self.gap_event = HCIGAPMsgs(self.buf[2])
        if self.gap_event == HCIGAPMsgs.HCI_VE_EVENT_CODE:
            self.conn_handle = struct.unpack("<H", bytes(self.buf[3:5]))[0]
            self.wireshark_out += [WSOutputElement(Protofields.BLE_HANDLE, self.conn_handle)]

    def __str__(self):
        info = " L2CAP Packet Received" if self.gap_event == HCIGAPMsgs.HCI_VE_EVENT_CODE else " L2CAP Packet Sent"
        string = self.gap_event.name + info
        if self.conn_handle is not None:
            string += " on handle " + str(self.conn_handle)
        return string


@dataclass
class LLSchedEvt(BLEEvent):
    """
    Base class for all scheduler events. This will be subclassed by individual scheduler events

    Args:
        ble_opcode: Opcode of event
        event: type of scheduler event

    """
    ble_opcode: BLEOpcode = BLEOpcode.LL_SCHED_EVT
    event: LLSchedEvtTypes = None

    def __post_init__(self):
        """Extract event type and continue building wireshark output"""
        super().__post_init__()
        self.event_type = LLSchedEvtTypes(self.swo_frame.values[0])
        self.wireshark_out += [WSOutputElement(Protofields.BLE_OPCODE, self.ble_opcode.name),
                               WSOutputElement(Protofields.BLE_LAYER, "LL"),
                               WSOutputElement(Protofields.BLE_EVENT, self.event.name)]

    def __str__(self):
        return "%s : " % self.event.name


@dataclass
class LLSchedPostRF(LLSchedEvt):
    """Post RF event sent after receiving an interrupt after an RF command has run"""
    event: LLSchedEvtTypes = LLSchedEvtTypes.POST_RF

    def __post_init__(self):
        """Extract handle, contrller task ID, and continue building wireshark output"""
        super().__post_init__()
        self.handle = self.swo_frame.values[1]
        self.task_id = LLTaskIds(self.swo_frame.values[2])
        if self.handle != 0xFFFF:
            self.wireshark_out += [WSOutputElement(Protofields.BLE_HANDLE, self.handle)]
        self.wireshark_out += [WSOutputElement(Protofields.BLE_LL_TASK, self.task_id.name)]

    def __str__(self):
        string = "Task ID %s " % self.task_id.name
        if self.handle != 0xFFFF:
            string += str(self.handle)
        return super().__str__() + string


@dataclass
class LLSchedNextSched(LLSchedEvt):
    """Event sent when the scheduler schedules the next RF command"""
    event: LLSchedEvtTypes = LLSchedEvtTypes.SCHED_NEXT

    def __post_init__(self):
        """Extract event type, controler task ID, and scheduled start time"""
        super().__post_init__()
        self.task_id = LLTaskIds(self.swo_frame.values[1])
        self.start_time = self.swo_frame.values[2]

    def __str__(self):
        return super().__str__() + "Scheduled %s @ %f s" % (self.task_id.name, self.start_time / 1000000)


@dataclass
class LLFindNextSecTask(LLSchedEvt):
    event: LLSchedEvtTypes = LLSchedEvtTypes.FIND_NEXT_SEC_TASK

    def __post_init__(self):
        super().__post_init__()
        self.task_id = LLTaskIds(self.swo_frame.values[1])
        self.start_time = self.swo_frame.values[2]

    def __str__(self):
        return super().__str__() + "Next Secondary Task is {} @ {} s".format(self.task_id.name, self.start_time / 1000000)


@dataclass
class LLFindStartType(LLSchedEvt):
    event: LLSchedEvtTypes = LLSchedEvtTypes.FIND_START_TYPE

    def __post_init__(self):
        super().__post_init__()
        self.start_type = LLTaskTypes(self.swo_frame.values[1])
        self.start_time = self.swo_frame.values[2] if self.start_type is LLTaskTypes.LL_SCHED_START_EVENT else None

    def __str__(self):
        string = super().__str__() + "Secondary task Start Type is {}: {}".format(self.start_type.name,
                                                                                  LLTaskTypeToString[self.start_type])
        if self.start_time is not None:
            string += " ({})".format(self.start_time / 1000000)
        return string


@dataclass
class LLRfCbEvent(LLSchedEvt):
    event: LLSchedEvtTypes = LLSchedEvtTypes.RF_CB_EVENT

    def __post_init__(self):
        super().__post_init__()
        self.rf_event = self.swo_frame.values[1]

    def __str__(self):
        return "{} ({})".format(super().__str__(),
                                ", ".join([RfEvents(2**k).name for k, v in enumerate(bin(self.rf_event)[:1:-1]) if int(v)][::-1]))

osal_messages = {
    1: ControllerToHostEventMsg,
    2: "Host to Controller Command",
    3: "Host to Controller Data",
    5: "HCI Disconnection Complete Event",
    16: "HCI Command Status",
    144: HCIDataEventMsg,
    145: EventEventMsg,
    146: EventEventMsg,
    148: HCIEventMsg,
    160: L2CAPDataInMsg,
    161: L2CAPDataOutMsg,
    176: GATTDataMsg,
    177: "Incoming GATTServApp message",
    178: "Incoming Signaling message",
    208: GAPOsalMessage
}

ll_sched_evts = {
    0: LLSchedPostRF,
    1: LLSchedNextSched,
    2: LLFindNextSecTask,
    3: LLFindStartType,
    4: None,
    5: LLRfCbEvent
}


class BLEFramer(FramerBase):
    """Builds BLE frames from SWO frames"""

    def __init__(self):
        self.layer_int_to_str = {}

    def reset(self):
        """Handle a reset frame by resetting layer integer to string mapping"""
        self.layer_int_to_str = {}

    def parse(self, swo_frame=None):
        """
        Parse an input SWO Frame into a BLE Frame

        Args:
          swo_frame:  input SWO frame

        Returns:
            ble_frame: A newly built BLEFrame if parsed correctly or the input SWOFrame otherwise

        """
        try:
            # Is this an OSAL Event?
            if swo_frame.opcode == SWOOpcode.EVENT and swo_frame.event == "OSAL_EVT":
                ble_frame = OSALEvent(swo_frame=swo_frame, layer_map=self.layer_int_to_str)
            # Is this an LL Scheduler Event?
            elif swo_frame.opcode == SWOOpcode.EVENT and swo_frame.event == "SCHED_EVT":
                ble_frame = ll_sched_evts[swo_frame.values[0]](swo_frame=swo_frame)
            # Is this an OSAL Message?
            elif swo_frame.opcode == SWOOpcode.EVENT_SET and swo_frame.event == "OSAL_MSG":
                # Parse SWO frame based on even type (byte 1 of the buffer)
                ble_frame = osal_messages[swo_frame.events[0].buf[1]](swo_frame=swo_frame,
                                                                      layer_map=self.layer_int_to_str)
            # Is this the initial task initialization
            elif swo_frame.opcode == SWOOpcode.EVENT_SET and swo_frame.event == "TASK_INIT":
                # Build tasks dict
                for x in swo_frame.events:
                    val, name = x.string.split(" ")
                    self.layer_int_to_str.update({int(val): name})
                    logger.debug("Task init: Task {} set to {}".format(val, name))
                # This is not for output. It has been consumed by the BLE parser
                ble_frame = None
            else:
                # This was not parsed. The same input SWO frame will be returned
                ble_frame = swo_frame
                logger.error("new event " + str(ble_frame))
                return ble_frame
            # Output now
            if ble_frame is not None:
                logger.info(str(ble_frame))
                # Add info and close tree
                ble_frame.wireshark_out += [WSOutputElement(Protofields.COMMON_INFO, str(ble_frame)),
                                            WSOutputElement(Protofields.COMMON_CLOSE_TREE)]
            return ble_frame
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error("{} @ {} {}: ".format(exc_type, fname, exc_tb.tb_lineno) + str(e))
