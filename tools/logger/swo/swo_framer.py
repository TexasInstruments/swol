"""
Parse serial data using the SWO Protocol as defined TODO: here
"""

import logging
import enum
from collections import deque
import math
from abc import ABC, abstractmethod
import os
import sys
from dataclasses import *
from itm import ITMOpcode, build_value, ITMStimulusPort
from wireshark_output import WSOutputElement, Protofields

VERBOSE_FRAMING = 0  # Display ITM frames and SWO framing information
VERBOSE_SWO = 0 # If 0, all SWO logging below info is turned off

logger = logging.getLogger("SWO Framer")

class LoggingFilter(logging.Filter):
    """Implement logging filter"""

    def filter(self, record):
        """Test whether to filter out message

        Args:
          record: message to filter on

        Returns:
          True: display (don't filter)
          False: don't display (do filter)

        """
        if not VERBOSE_SWO and record.levelno < 30:
            return False
        if not VERBOSE_FRAMING:
            return not record.getMessage().startswith("FRAMING")
        else:
            return True

SWO_SWIT_SIZE = 4

SWO_RESET_TOKEN = bytes([0xBB, 0xBB, 0xBB, 0xBB])

AccessTypeDict = {0x0: "Disabled",
                  0x1: "EmitPc",
                  0x2: "EmitDataOnReadWrite",
                  0x3: "SamplePcAndEmitDataOnReadWrite",
                  0xC: "SampleDataOnRead",
                  0xD: "SampleDataOnWrite",
                  0xE: "SamplePcAndDataOnRead",
                  0xF: "SamplePcAndDataOnWrite"}

class TimeSyncState(enum.Enum):
    SECONDS = 0
    SUBSECONDS = 1

class EnqueueLocation(enum.Enum):
    LEFT = 0
    RIGHT = 1

class ParseState(enum.Enum):
    EVENT_SET_INFO = 0
    LENGTH = 1
    DATA = 2

class SWOOpcode(enum.Enum):
    """ """
    FORMATTED_TEXT = 0
    EVENT = 1
    EVENT_SET_START = 2
    EVENT_SET_END = 3
    BUFFER = 4
    BUFFER_OVERFLOW = 5
    WATCHPOINT = 6
    SYNC_TIME = 7
    HW_DATA_TRACE = 8
    EVENT_SET = 9
    PC_SAMPLE_TRACE = 10
    RESET = 11
    EVENT_CREATION = 0xFF


class FrameBase(ABC):
    """The base frame that should be inherited by frames of all custom modules."""

    @property
    @abstractmethod
    def wireshark_out(self):
        """
        Recipe for wireshark_output module to send to wireshark

        List of wireshark_output.WSOutputElement named tuples that will be used to build stream to send to wireshark

        """
        return

    @wireshark_out.setter
    @abstractmethod
    def wireshark_out(self, value):
        return


class FramerBase(ABC):
    """The base framer that should be inherited by all custom modules"""

    @abstractmethod
    def parse(self, frame):
        """
        Turn input frame into per-module frame

        Args:
          frame: input frame (ITM for SWO module and SWO frame for other modules)

        Returns:
            parsed frame

        """
        return

    @abstractmethod
    def reset(self):
        """Receive reset signal and reset module if / as needed"""
        return


@dataclass
class SWOFrame(FrameBase):
    """Base SWO frame that will be subclassed by other SWO Frame types"""
    rat_ts_s: float = 0
    rtc_ts_s: float = 0
    rat_ts_t: float = 0
    opcode: SWOOpcode = None
    file: str = ""
    line: str = ""
    level: str = ""
    module: str = ""
    wireshark_out: list = None

    def build_output(self):
        """Build wirshark output"""
        self.wireshark_out = [WSOutputElement(Protofields.SWO_RAT_S, self.rat_ts_s),
                              WSOutputElement(Protofields.SWO_RAT_T, self.rat_ts_t),
                              WSOutputElement(Protofields.SWO_RTC_S, self.rtc_ts_s),
                              WSOutputElement(Protofields.SWO_OPCODE, self.opcode.name),
                              WSOutputElement(Protofields.SWO_MODULE, self.module),
                              WSOutputElement(Protofields.SWO_LEVEL, self.level),
                              WSOutputElement(Protofields.SWO_FILE, self.file),
                              WSOutputElement(Protofields.SWO_LINE, self.line)]


class SWOSoftwareFrame(SWOFrame):
    """
    Base SWO frame that will be subclassed by other software frames

    Args:
        rat_ts_s: radio time in seconds
        rtc_ts_s: real-time-clock in seconds
        rat_ts_t: radio time in ticks
        header: SWO header (first byte of ITM software source frame)
        trace_db: database built from  elf file

    """

    def __init__(self, rat_ts_s, rtc_ts_s, rat_ts_t, elf_string=None, trace_db=None):
        self.rat_ts_s = rat_ts_s
        self.rtc_ts_s = rtc_ts_s
        self.rat_ts_t = rat_ts_t
        self.is_event_set = False
        self._trace_db = trace_db
        self.remaining_length = 0
        self._deferred = None
        self._is_event_set = None
        self.string = ""
        self._output = False
        if elf_string is not None:
            self.opcode = elf_string.opcode

    @property
    def output(self):
        """Return whether or not this frame should be outputted (e.g. to wireshark)"""
        output = self._output if not self.is_event_set else False
        return output

    @property
    def deferred(self):
        return self._deferred

    @deferred.setter
    def deferred(self, arg):
        self._deferred = False if arg == "0" or arg == "0U" or arg == "FALSE" else True

    @property
    def is_event_set(self):
        return self._is_event_set

    @is_event_set.setter
    def is_event_set(self, arg):
        self._is_event_set = False if arg == "0" or arg == "0U" or arg == "FALSE" else True

    def parse(self, itm_frame):
        """Base parsing for software frame. Subclassed frames will extend this"""
        # Adjust for special three byte case...discard last byte
        if self.remaining_length == 3:
            itm_frame.data.pop()
            itm_frame.size = 3
        # Adjust remaining length
        self.remaining_length -= len(itm_frame)

    def __str__(self):
        return "RAT: {:.7f}s, RTC: {:.7f}s : {} @ {}({}, {}) --> {} ".format(
            self.rat_ts_s, self.rtc_ts_s, self.file, str(self.line), self.module, self.level, self.opcode.name)


class SWOFormattedTextFrame(SWOSoftwareFrame):
    """
    SWO Formatted text (printf) frame.

    Extract elf strings, event set information if it exists, and remainin length

    Args:
        rat_ts_s: radio time in seconds
        rtc_ts_s: real-time-clock in seconds
        rat_ts_t: radio time in ticks
        header: SWO header (first byte of ITM software source frame)
        trace_db: database built from elf file

    """

    def __init__(self, rat_ts_s, rtc_ts_s, rat_ts_t, elf_string, trace_db):
        super().__init__(rat_ts_s, rtc_ts_s, rat_ts_t, elf_string, trace_db)
        self.values = []
        self._output = True
        self.parse_state = ParseState.DATA
        # Parse elf string
        self.deferred, self.is_event_set, self.file, self.line, self.level, self.module, \
            self.string, self._nargs = elf_string.value.split(":::")
        self._nargs = int(self._nargs)
        # Set remaining length
        self.remaining_length = self._nargs * SWO_SWIT_SIZE
        # Alert of formatting error
        if self._nargs > 1 and self._nargs != self.string.count("%"):
            self.string += "[ARGUMENT MISMATCH]"
        # Expect a one-byte packet to complete header if this is an event set
        if self.is_event_set:
            self.parse_state = ParseState.EVENT_SET_INFO
            self.remaining_length = self.remaining_length + 2

    def parse(self, itm_frame):
        """Append value to list of values and format string if complete frame has been received"""
        super().parse(itm_frame)
        if self.parse_state is ParseState.DATA:
            if self._nargs == self.string.count("%"):
                # Build 32-bit value and append
                self.values.append(build_value(itm_frame.data))
                # Format string if we've received all data
                if self.remaining_length == 0:
                    self.string = self.string % (tuple(self.values))
        elif self.parse_state is ParseState.EVENT_SET_INFO:
            self.parse_state = ParseState.DATA
            # Extract record and handle
            self.record, self.handle = itm_frame.data

    def __str__(self):
        # Indicate if this is an individual record in an event set
        string = "Event Record, " + self.string if self.is_event_set else self.string
        return super().__str__() + string

    def build_output(self):
        """Extend wireshark output"""
        info = self.__str__().replace(super().__str__(), "")
        super().build_output()
        self.wireshark_out += [WSOutputElement(Protofields.SWO_INFO, info),
                               WSOutputElement(Protofields.COMMON_INFO, info)]


class SWOEventFrame(SWOSoftwareFrame):
    """
    SWO Event Frame

    Extract meta of event creation and event call and find remaining length

    Args:
        rat_ts_s: radio time in seconds
        rtc_ts_s: real-time-clock in seconds
        rat_ts_t: radio time in ticks
        header: SWO header (first byte of ITM software source frame)
        trace_db: database built from elf file

    """

    def __init__(self, rat_ts_s, rtc_ts_s, rat_ts_t, elf_string, trace_db):
        super().__init__(rat_ts_s, rtc_ts_s, rat_ts_t, elf_string, trace_db)
        self.values = []
        self._output = True
        # Store elf string info from event call
        self.deferred, self.is_event_set, self.file, self.line, self.level, self.module, \
            self.event, self.remaining_length = elf_string.value.split(":::")
        # Find corresponding event elf string
        elf_event = self._trace_db.eventDB[self.module + self.event]
        # Overwrite string with the string from the event creation
        self.string = elf_event.string
        # Find remaining length
        self.remaining_length = (
            int(self.remaining_length) - 1) * SWO_SWIT_SIZE

    def parse(self, itm_frame):
        """Append event value to values list"""
        super().parse(itm_frame)
        # Build 32-bit value and append
        self.values.append(build_value(itm_frame.data))

    def __str__(self):
        return super().__str__() + "{}: {}".format(self.string,
                                                   " ".join("{0:#0{1}x}".format(x, 10) for x in self.values))

    def build_output(self):
        """Extend wireshark output"""
        info = self.__str__().replace(super().__str__(), "")
        super().build_output()
        self.wireshark_out += [WSOutputElement(Protofields.SWO_INFO, info),
                               WSOutputElement(Protofields.SWO_EVENT, self.event),
                               WSOutputElement(Protofields.COMMON_INFO, info)]


class SWOEventSetStartFrame(SWOSoftwareFrame):
    """
    SWO Event Set Start Frame

    Extract event set information, and set remaining length to look for secondary header

    Args:
        rat_ts_s: radio time in seconds
        rtc_ts_s: real-time-clock in seconds
        rat_ts_t: radio time in ticks
        header: SWO header (first byte of ITM software source frame)
        trace_db: database built from elf file

    """

    def __init__(self, rat_ts_s, rtc_ts_s, rat_ts_t, header, trace_db):
        super().__init__(rat_ts_s, rtc_ts_s, rat_ts_t, header, trace_db)
        self.opcode = SWOOpcode.EVENT_SET_START
        # Parse elf string
        _, self.is_event_set, self.file, self.line, self.module, self.level, self.event, _ = header.value.split(":::")
        # Set remaining length
        self.remaining_length = 1

    def parse(self, itm_frame):
        """Append event value to values list"""
        super().parse(itm_frame)
        # Build 32-bit value and append
        self.handle = itm_frame.data[0]

    def __str__(self):
        return super().__str__() + "Handle {}: {} ".format(self.handle, self.event)

    def build_output(self):
        """Extend wireshark output"""
        info = self.__str__().replace(super().__str__(), "")
        super().build_output()
        self.wireshark_out += [WSOutputElement(Protofields.SWO_INFO, info),
                               WSOutputElement(Protofields.COMMON_INFO, info)]


class SWOEventSetEndFrame(SWOSoftwareFrame):
    """
    SWO Event Set End Frame

    Extract event set information and event creation meta

    Args:
        rat_ts_s: radio time in seconds
        rtc_ts_s: real-time-clock in seconds
        rat_ts_t: radio time in ticks
        header: SWO header (first byte of ITM software source frame)
        trace_db: database built from elf file

    """

    def __init__(self, rat_ts_s, rtc_ts_s, rat_ts_t, header, trace_db):
        super().__init__(rat_ts_s, rtc_ts_s, rat_ts_t, header, trace_db)
        self.opcode = SWOOpcode.EVENT_SET_END
        # Parse elf string
        _, self.is_event_set, self.file, self.line, self.module, self.level, _, _ = header.value.split(":::")
        # One byte to find event set ID
        self.remaining_length = 1

    def parse(self, itm_frame):
        """Add received buffer portion to cumulative data buffer"""
        super().parse(itm_frame)
        self.handle = itm_frame.data[0]

    def __str__(self):
        return super().__str__() + "Handle %d: %s " % (self.handle, self.string)

    def build_output(self):
        """Extend wireshark output"""
        info = self.__str__().replace(super().__str__(), "")
        super().build_output()
        self.wireshark_out += [WSOutputElement(Protofields.SWO_INFO, info),
                               WSOutputElement(Protofields.COMMON_INFO, info)]


class SWOBufferFrame(SWOSoftwareFrame):
    """
    SWO Buffer (data + string) Frame

    Extract event set information buffer call meta and find remaining length
    to determine if there will be a secondary header

    Args:
        rat_ts_s: radio time in seconds
        rtc_ts_s: real-time-clock in seconds
        rat_ts_t: radio time in ticks
        header: SWO header (first byte of ITM software source frame)
        trace_db: database built from elf file

    """

    def __init__(self, rat_ts_s, rtc_ts_s, rat_ts_t, elf_string, trace_db):
        super().__init__(rat_ts_s, rtc_ts_s, rat_ts_t, elf_string, trace_db)
        self.buf = []
        self._output = True
        # Parse elf string
        self.deferred, self.is_event_set, self.file, self.line, self.level, self.module, \
            self.string, _ = elf_string.value.split(":::")
        # Set parse state
        self.parse_state = ParseState.EVENT_SET_INFO if self.is_event_set else ParseState.LENGTH
        # We will always receive a 4-byte packet with the length of the buffer
        # Expect an additional two byte packet to complete header if this is an event set
        self.remaining_length = 6 if self.is_event_set else 4

    def parse(self, itm_frame):
        """Add received buffer portion to cumulative data buffer"""
        super().parse(itm_frame)
        if self.parse_state is ParseState.EVENT_SET_INFO:
            self.parse_state = ParseState.LENGTH
            # Extract record and handle
            self.record, self.handle = itm_frame.data
        elif self.parse_state is ParseState.LENGTH:
            self.parse_state = ParseState.DATA
            # Find remaining length
            self.remaining_length = build_value(itm_frame.data)
        elif self.parse_state is ParseState.DATA:
            self.buf.extend(itm_frame.data)


    def __str__(self):
        # Handle format tokens
        token_offset = self.string.find("%!", 0)
        string = ""
        if token_offset > 0:
            if self.string[token_offset + 2] == "S":
                string = self.string.replace("%!S", "{}").format(bytes(self.buf).decode("utf-8"))
            elif self.string[token_offset + 2] == "E":
                tmp = self.buf.copy()
                tmp.reverse()
                string = self.string.replace("%!E", "{}").format(" ".join("{0:#0{1}x}".format(x, 4) for x in tmp))
        else:
            string = "{} {}".format(self.string, " ".join("{0:#0{1}x}".format(x, 4) for x in self.buf))
        # Indicate if this is an individual record in an event set
        if self.is_event_set:
            string = "Event Record, " + string
        return super().__str__() + string

    def build_output(self):
        """Extend wireshark output"""
        info = self.__str__().replace(super().__str__(), "")
        super().build_output()
        self.wireshark_out += [WSOutputElement(Protofields.SWO_INFO, info),
                               WSOutputElement(Protofields.COMMON_INFO, info)]


class SWOBufferOverflowFrame(SWOSoftwareFrame):
    """
    SWO Buffer Overflow indicating device's internal buffer for deferred SWO data is full

    Extract meta information for the call that caused the overflow

    Args:
        rat_ts_s: radio time in seconds
        rtc_ts_s: real-time-clock in seconds
        rat_ts_t: radio time in ticks

    """

    def __init__(self, rat_ts_s, rtc_ts_s, rat_ts_t):
        super().__init__(rat_ts_s, rtc_ts_s, rat_ts_t)
        self.opcode = SWOOpcode.BUFFER_OVERFLOW
        self._output = True

    def __str__(self):
        return ("WARNING!!! BUFFER_OVERFLOW : RAT: {:.7f} s, RTC: {:.7f} s : {}".format(
            self.rat_ts_s, self.rtc_ts_s, "from " + self.opcode.name))

    def build_output(self):
        """Build wireshark output"""
        info = "WARNING!!! BUFFER_OVERFLOW" + self.string
        self.wireshark_out = [WSOutputElement(Protofields.SWO_RAT_S, self.rat_ts_s),
                              WSOutputElement(Protofields.SWO_RTC_S, self.rtc_ts_s),
                              WSOutputElement(Protofields.SWO_RAT_T, self.rat_ts_t),
                              WSOutputElement(Protofields.SWO_OPCODE, self.opcode.name),
                              WSOutputElement(Protofields.SWO_INFO, info),
                              WSOutputElement(Protofields.COMMON_INFO, info)]


class SWOWatchpointEnableFrame(SWOSoftwareFrame):
    """
    SWO Watchpoint Enable Frame

    Extract address and string to associate with watchpoint that was set so that this information can be displayed
    when the watchpoint data is received.

    Args:
        rat_ts_s: radio time in seconds
        rtc_ts_s: real-time-clock in seconds
        rat_ts_t: radio time in ticks
        header: SWO header (first byte of ITM software source frame)
        trace_db: database built from elf file

    """

    def __init__(self, rat_ts_s, rtc_ts_s, rat_ts_t, header, trace_db):
        super().__init__(rat_ts_s, rtc_ts_s, rat_ts_t, header)
        self.opcode = SWOOpcode.WATCHPOINT
        self.deferred = "FALSE"
        # Store information from elf string
        self.watchpoint, self.function, self.file, self.line, self.level, self.module, \
            self.wp_string, _ = header.value.split(":::")
        # Extract integer from watchpoint string
        self.watchpoint = int(self.watchpoint[-1])

    def __str__(self):
        return super().__str__() + self.string + " ( " + self.function + ")"

    def build_output(self):
        """Extend wireshark output"""
        info = self.__str__().replace(super().__str__(), "")
        super().build_output()
        self.wireshark_out += [WSOutputElement(Protofields.SWO_INFO, info),
                               WSOutputElement(Protofields.COMMON_INFO, info)]


class SWOEventSet(SWOSoftwareFrame):
    """
    SWO Event Set

    Turns a list of events into an event set. The event list is first sorted into a list.The meta information from the
    Event Set Start (the first event in the event list) is used for this frame and the event set start is then deleted.

    Args:
        events: list of events that are part of the event set

    """

    def __init__(self, events):
        # Sort dictionary of events and store in list
        _, self.events = zip(*(sorted(events.items())))
        super().__init__(self.events[0].rat_ts_s, self.events[0].rtc_ts_s, self.events[0].rat_ts_t)
        self.opcode = SWOOpcode.EVENT_SET
        self._output = True
        # Overwrite event set init metadata from first event (assuming it exists)
        self.event = self.events[0].event
        self.module = self.events[0].module
        self.level = ""
        self.file = self.events[0].file
        self.line = self.events[0].line
        self.string = self.events[0].string
        # Remove the event set start frame now that we've consumed its information
        self.events = list(self.events[1:])

    def __str__(self):
        string = "RAT: {:.7f} s, RTC: {:.7f} s --> {} ".format(self.rat_ts_s, self.rtc_ts_s, self.opcode.name)
        return string + "\n      " + "\n      ".join([str(x) for x in self.events])

    def build_output(self):
        """Extend wireshark output, adding the wireshark output from each event in the event list as a tree"""
        super().build_output()
        # Overwrite tree open string
        for x in self.events:
            x.wireshark_out[0] = WSOutputElement(Protofields.COMMON_OPEN_TREE, "Event %d" % x.record)
            # Skip info since it will be overwritten below
            del x.wireshark_out[-2]
            self.wireshark_out.extend(x.wireshark_out)
        self.wireshark_out += [WSOutputElement(Protofields.SWO_INFO, "See Tree of Events"),
                               WSOutputElement(Protofields.SWO_EVENT, self.event),
                               WSOutputElement(Protofields.COMMON_INFO, "See Tree of Events")]
        pass


class SWOResetFrame(SWOSoftwareFrame):
    """
    SWO Reset Frame

    Build reset frame after receiving reset token.

    Args:
        rat_ts_s: radio time in seconds
        rtc_ts_s: real-time-clock in seconds
        rat_ts_t: radio time in ticks

    """

    def __init__(self, rat_ts_s, rtc_ts_s, rat_ts_t):
        super().__init__(rat_ts_s, rtc_ts_s, rat_ts_t)
        self.remaining_length = 0
        self.opcode = SWOOpcode.RESET
        self._output = True

    def __str__(self):
        return super().__str__() + "Device Reset"

    def build_output(self):
        """Extend wireshark output"""
        super().build_output()
        self.wireshark_out += [WSOutputElement(Protofields.SWO_INFO, self.__str__()),
                               WSOutputElement(Protofields.COMMON_INFO, self.__str__())]


class SWOHWDataFrame(SWOFrame):
    """
    SWO Hardware Data Frame

    Store hardware data and find string of associated watchpoint

    Args:
        itm_frame: input ITMFrame
        watchpoints: dictionary of watchpoint string information
        rat_ts_s: radio time in seconds
        rtc_ts_s: real-time-clock in seconds
        rat_ts_t: radio time in ticks

    """

    def __init__(self, itm_frame, watchpoints, rat_ts_s, rtc_ts_s, rat_ts_t):
        self.opcode = SWOOpcode.HW_DATA_TRACE
        self.itm_string = str(itm_frame)
        self.hw_wp_comparator = itm_frame.comparator
        self.wp_string = watchpoints[self.hw_wp_comparator]
        self.output = True
        self.rat_ts_s = rat_ts_s
        self.rtc_ts_s = rtc_ts_s
        self.rat_ts_t = rat_ts_t
        self.remaining_length = 0

    def __str__(self):
        return ("RAT: {:.7f} s, RTC: {:.7f} s -> {} : {}".format(
            self.rat_ts_s, self.rtc_ts_s, self.wp_string + " : " + self.itm_string, self.opcode.name))

    def build_output(self):
        """Build wireshark output"""
        self.wireshark_out = [WSOutputElement(Protofields.SWO_RAT_S, self.rat_ts_s),
                              WSOutputElement(Protofields.SWO_RAT_T, self.rat_ts_t),
                              WSOutputElement(Protofields.SWO_RTC_S, self.rtc_ts_s),
                              WSOutputElement(Protofields.SWO_OPCODE, self.opcode.name),
                              WSOutputElement(Protofields.SWO_INFO, self.wp_string + " : " + self.itm_string),
                              WSOutputElement(Protofields.COMMON_INFO, self.wp_string + " : " + self.itm_string)]


class SWOHWPCSample(SWOFrame):
    """
    SWO Hardware Program Counter Frame

    Using trace database, find function name that the program counter corresponds to.

    Args:
        itm_frame: input ITMFrame
        db: trace database
        rat_ts_s: radio time in seconds
        rtc_ts_s: real-time-clock in seconds
        rat_ts_t: radio time in ticks

    """

    def __init__(self, itm_frame, db, rat_ts_s, rtc_ts_s, rat_ts_t):
        self.opcode = SWOOpcode.PC_SAMPLE_TRACE
        self.itm_string = str(itm_frame)
        self.pc_counter = itm_frame.value
        self.output = True
        self.rat_ts_s = rat_ts_s
        self.rtc_ts_s = rtc_ts_s
        self.rat_ts_t = rat_ts_t
        self.remaining_length = 0
        # Get function name
        fxn, file, line = db.get_info_for_address(self.pc_counter)
        if fxn != b'<Function not in dict>':
            self.string = ("%s (%s:%d)" % (fxn.decode('utf-8'), file.decode('utf-8'), line))
        else:
            self.string = "<skip>"

    def __str__(self):
        return "RAT: {:.7f} s, RTC: {:.7f} s -> {}".format(self.rat_ts_s, self.rtc_ts_s, self.string)

    def build_output(self):
        """Build wireshark output"""
        self.wireshark_out = [WSOutputElement(Protofields.SWO_RAT_S, self.rat_ts_s),
                              WSOutputElement(Protofields.SWO_RAT_T, self.rat_ts_t),
                              WSOutputElement(Protofields.SWO_RTC_S, self.rtc_ts_s),
                              WSOutputElement(Protofields.SWO_OPCODE, self.opcode.name),
                              WSOutputElement(Protofields.SWO_INFO, self.itm_string),
                              WSOutputElement(Protofields.COMMON_INFO, self.string)]


frame_opcode_dict = {SWOOpcode.FORMATTED_TEXT: SWOFormattedTextFrame,
                     SWOOpcode.EVENT: SWOEventFrame,
                     SWOOpcode.EVENT_SET_START: SWOEventSetStartFrame,
                     SWOOpcode.EVENT_SET_END: SWOEventSetEndFrame,
                     SWOOpcode.BUFFER: SWOBufferFrame,
                     SWOOpcode.WATCHPOINT: SWOWatchpointEnableFrame}


def rat_from_rtc(rtc_s):
    """
    Turn a real-time clock value into a radio time value

    Args:
      rtc_s: real-time-clock in seconds

    Returns:
        rat_s: radio time in seconds
        rat_t: radio time in ticks

    """
    # Updated assumed RAT tick based on RTC value (magic magic)
    # Doing the same assumptions as done inside the RF  (0x100000000LL/32768)
    # RTC in ticks like on our devices
    rtc_sec = int((math.floor(rtc_s) * 32768))
    rtc_subsec = int((rtc_s - rtc_sec) * 2 ** 32)
    new_rat = (rtc_sec << 32) + rtc_subsec
    # Conservatively assume that we are just about to increment
    # the RTC Scale with the 4 MHz that the RAT is running
    # Add the RAT offset for RTC == 0 * /
    new_rat += 4294967296 / 32768
    new_rat *= 4000000  # Scale to 4 MHz ticks
    new_rat = new_rat / 4294967296
    # Store as ticks
    rat_t = new_rat
    # Store as time
    rat_s = new_rat / 4000000
    return rat_s, rat_t


class SWOFramer(FramerBase):
    """
    Manages parsing ITM frames into SWO frames

    Stores a sorted dictionary of frames as they are being parsed.
    Stores a dictionary of watchpoint strings to match to corresponding watchpoints.
    Stores a trace database for use by members.
    Stores a dictionary of event sets as they are being build from indivual SWO frames.

    Args:
        db: trace database
        clock: clock speed of embedded device

    """

    def __init__(self, db=None, clock=48000000, baud=12000000):
        # Set up logging
        logger.addFilter(LoggingFilter())
        self._trace_db = db
        self._immediate_frames = deque()
        self._deferred_frames = deque()
        self._event_sets = {}
        self._watchpoints = [None] * 4
        self._rat_t = 0
        self._rat_s = 0
        self._rtc_s = 0
        self.clock = clock
        self.offset = 0
        self.baudrate = int(baud)
        self.time_sync_state = TimeSyncState.SECONDS


    def enqueue(self, frame, location):
        # Add to appropriate frame queue
        q = self._deferred_frames if frame.deferred and frame.parse_state is ParseState.DATA else self._immediate_frames
        q.append(frame) if location is EnqueueLocation.RIGHT else q.appendleft(frame)

    def parse(self, itm_frame=None):
        """
        The top-level ITMFrame parser.

        Will directly build all frames besides software source frames (these are build by build_sw_source_frame).
        When a timestamp is received from ITM, the running time values will be updated.
        After all frames are built, completed() will be called.

        Args:
          itm_frame: input ITMFrame

        Returns:

        """
        try:
            # logger.debug("FRAMING " + str(itm_frame))
            frame = None
            if itm_frame.opcode == ITMOpcode.TIMESTAMP:
                # Update running timestamps then discard the frame
                self._rtc_s += itm_frame.ts_counter / self.clock
                self._rat_s, self._rat_t = rat_from_rtc(self._rtc_s)
                self.offset = 0
            elif itm_frame.opcode == ITMOpcode.SOURCE_SW:
                self.offset += (len(itm_frame) + 1) * 1 / self.baudrate
                # This may not be the entire frame. Try to build it.
                frame = self.build_sw_source_frame(itm_frame, self.offset)
                if frame is not None and frame.remaining_length == 0:
                    frame = self.swit_completed(frame, itm_frame)
            elif itm_frame.opcode == ITMOpcode.TRACE:
                self.offset += (len(itm_frame) + 1) * 1 / self.baudrate
                # This is the entire frame. Create and parse now.
                frame = SWOHWDataFrame(itm_frame, self._watchpoints, self._rat_s + self.offset,
                                       self._rtc_s + self.offset, self._rat_t)
            elif itm_frame.opcode == ITMOpcode.PACKET_PC:
                self.offset += (len(itm_frame) + 1) * 1 / self.baudrate
                frame = SWOHWPCSample(itm_frame, self._trace_db, self._rat_s + self.offset, self._rtc_s + self.offset,
                                      self._rat_t)
                if frame.string == "<skip>":
                    frame = None  # Only return frames that have meaningful PC strings
            # Handle global framer functionality if frame is complete
            frame = self.completed(frame) if frame is not None and frame.remaining_length == 0 else None
            return frame
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error("{} @ {} {}: ".format(exc_type, fname, exc_tb.tb_lineno) + str(e))

    def build_sw_source_frame(self, itm_frame=None, offset=0):
        """
        Parsed ITM Software Source frames into SWO frames

        Based on the stimulus port and packet length, frames will be added / removed from the internal frames
        queue until completed.

        Args:
          itm_frame:

        Returns:
            frame: new SWO frame if parsed, otherwise input ITM frame

        """
        try:
            frame = None
            # Check port to see if this is a new frame
            if itm_frame.port == ITMStimulusPort.STIM_HEADER:
                # Get elf data from header
                try:
                    header = build_value(itm_frame.data)
                    elf_string = self._trace_db.traceDB[header]
                except KeyError:
                    # This address does not exist in the trace database
                    logger.warning("FRAMING: corruption: no trace database information at {}".format(hex(header)))
                    return None
                # Build new frame
                try:
                    frame = frame_opcode_dict[elf_string.opcode](self._rat_s + offset, self._rtc_s + offset,
                                                                 self._rat_t, elf_string, self._trace_db)
                except KeyError:
                    # Unknown Frame type, print error.
                    logger.warning('FRAMING: corruption: unknown opcode 0x%x' % elf_string.opcode.value)
                    return None
                # Add to appropriate queue
                self.enqueue(frame, EnqueueLocation.RIGHT)
                logger.debug('FRAMING: New Frame of opcode {}, len {}'.format(frame.opcode.name, frame.remaining_length))
            elif itm_frame.port == ITMStimulusPort.STIM_IDLE:
                # Get frame on left of deferred queue
                frame = self._deferred_frames.popleft()
                # Add data to frame
                frame.parse(itm_frame)
                # Put back on left of deferred queue
                self.enqueue(frame, EnqueueLocation.LEFT)

            elif itm_frame.port == ITMStimulusPort.STIM_TRACE:
                try:
                    # Get frame from right of immediate queue
                    frame = self._immediate_frames.pop()
                    frame.parse(itm_frame)
                    logger.debug(
                        'FRAMING: {} Continue --> {} bytes received, remaining length: {}'.format(frame.opcode.name,
                                                                                                  len(itm_frame),
                                                                                                  frame.remaining_length))
                    # Put back on right of appropriate queue
                    self.enqueue(frame, EnqueueLocation.RIGHT)
                except Exception as e:
                    logger.error("Framing error: " + str(e))
                    logger.error("Discarding frame and attempting to continue.")

            elif itm_frame.port == ITMStimulusPort.STIM_SYNC_TIME:
                if self.time_sync_state is TimeSyncState.SECONDS:
                    self._rtc_s = build_value(itm_frame.data)
                    self.time_sync_state = TimeSyncState.SUBSECONDS
                else:
                    self._rtc_s = (build_value(itm_frame.data) / (2 ** 32)) + self._rtc_s
                    self._rat_s, self._rat_t = rat_from_rtc(self._rtc_s)
                    self.time_sync_state = TimeSyncState.SECONDS
                    logger.debug("FRAME_SYNC_TIME       : RTC: {:.7f} s".format(self._rtc_s))

            elif itm_frame.port == ITMStimulusPort.STIM_DRIVER:
                if SWO_RESET_TOKEN in itm_frame.data:
                    frame = SWOResetFrame(self._rat_s + offset, self._rtc_s + offset, self._rat_t)
                elif build_value(itm_frame.data) == 0xCCCCCCCC:
                    frame = SWOBufferOverflowFrame(self._rat_s + offset, self._rtc_s + offset, self._rat_t)
            else:
                # Print raw data
                logger.debug("Raw ITM Data: {}".format(" ".join(["0x{:02x}".format(x) for x in list(reversed(itm_frame.data))])))
            return frame
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error("{} @ {} {}: ".format(exc_type, fname, exc_tb.tb_lineno) + str(e))

    def swit_completed(self, swo_frame, itm_frame):
        """
        Perform actions on completed software source frames.

        Accumulate / build event set, store watchpoint string, update sync time, and handle reset frame.

        Args:
           frame: input SWO frame

        Returns:
           frame: event set frame if built otherwise input SWO frame

        """
        # Update event sets dict if needed
        try:
            if swo_frame.is_event_set:
                # Delete event set
                if swo_frame.opcode == SWOOpcode.EVENT_SET_END:
                    # Overwrite frame as sorted event set for returning
                    handle = swo_frame.handle
                    swo_frame = SWOEventSet(self._event_sets[handle])
                    # Delete event set from global event set dictionary
                    del self._event_sets[handle]
                else:
                    # Create event sets
                    if swo_frame.opcode == SWOOpcode.EVENT_SET_START:
                        self._event_sets[swo_frame.handle] = {}
                        self._event_sets[swo_frame.handle][0] = swo_frame
                        # Add to event sets
                        logger.debug(f"FRAMING: Create event set {swo_frame.handle}")
                    else:
                        self._event_sets[swo_frame.handle][swo_frame.record + 1] = swo_frame
                        logger.debug(f"FRAMING: Store record {swo_frame.record} of event set {swo_frame.handle}")
            # Update watchpoint dict if this frame is enabling a watchpoint
            elif swo_frame.opcode == SWOOpcode.WATCHPOINT:
                # Store in watchpoint list. Concatenate string passed at enable call with access type string
                self._watchpoints[swo_frame.watchpoint] = swo_frame.wp_string + " (" + swo_frame.function + ")"
            # Remove frame from deferred queue that corresponds to the overflow
            elif swo_frame.opcode == SWOOpcode.BUFFER_OVERFLOW:
                self._deferred_frames.pop()

            # Remove frame from queue
            if itm_frame.port in [ITMStimulusPort.STIM_TRACE, ITMStimulusPort.STIM_HEADER, ITMStimulusPort.STIM_IDLE]:
                logger.debug("FRAMING: Deleting SWO frame of opcode: %s" % swo_frame.opcode.name)
                self._deferred_frames.popleft() if swo_frame.deferred else self._immediate_frames.pop()

            # Display frame
            logger.info(str(swo_frame))
            return swo_frame
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error("{} @ {} {}: ".format(exc_type, fname, exc_tb.tb_lineno) + str(e))

    def reset(self):
        """Handle reset frame."""
        pass

    def completed(self, frame):
        """Build wireshark output"""
        # Build wireshark formatting and surround in a tree
        frame.build_output()
        if frame.wireshark_out is not None:
            frame.wireshark_out = [WSOutputElement(Protofields.COMMON_OPEN_TREE, "SWO Logger Frame")] + \
                                  frame.wireshark_out + [WSOutputElement(Protofields.COMMON_CLOSE_TREE)]

        return frame
