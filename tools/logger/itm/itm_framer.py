"""
Parse serial data using the ITM protcol as described in Appendix D4 (Debug ITM and DWT Packet Protofol) of the
ARM v7-M Architecture Reference Manual: https://developer.arm.com/docs/ddi0403/e/armv7-m-architecture-reference-manual
"""

import sys
import time
import logging
import queue
from dataclasses import *
from enum import Enum

verbose_timestamp = 0  # Show ITM timestamps
verbose_itm = 0  # Show ITM parsing debug info, not including timestamps

logger = logging.getLogger("ITM Framer")


class LoggingFilter(logging.Filter):
    """ Implement logging filter """

    def filter(self, record):
        """
        Test whether to filter out message

        Args:
          record: message to filter on

        Returns:
            True: display (don't filter)
            False: don't display (do filter)
        """
        # Only filter debug messages
        if record.levelname is "DEBUG":
            # Filter out timestamp logs
            if verbose_timestamp != 1 and record.getMessage().startswith("TIMESTAMP:"): return False
            # Filter out all logs other than timestamp
            if verbose_itm != 1 and not record.getMessage().startswith("TIMESTAMP:"): return False
            return True
        else:
            return True


MAX_ITM_FRAME_SIZE = 5

ITM_RESET_TOKEN = bytes([0x63, 0xBB, 0xBB, 0xBB, 0xBB])

HDR_OVERFLOW = 0x70


class ITMStimulusPort(Enum):
    """ ITM ports for software packets """
    STIM_RESV0 = 0
    STIM_RESV1 = 1
    STIM_RESV2 = 2
    STIM_RESV3 = 3
    STIM_RESV4 = 4
    STIM_RESV5 = 5
    STIM_RESV6 = 6
    STIM_RESV7 = 7
    STIM_RESV8 = 8
    STIM_RESV9 = 9
    STIM_RESV10 = 10
    STIM_SYNC_TIME = 11
    STIM_DRIVER = 12
    STIM_IDLE = 13
    STIM_HEADER = 14
    STIM_TRACE = 15
    STIM_RAW0 = 16
    STIM_RAW1 = 17
    STIM_RAW2 = 18
    STIM_RAW3 = 19
    STIM_RAW4 = 20
    STIM_RAW5 = 21
    STIM_RAW6 = 22
    STIM_RAW7 = 23
    STIM_RAW8 = 24
    STIM_RAW9 = 25
    STIM_RAW10 = 26
    STIM_RAW11 = 27
    STIM_RAW12 = 28
    STIM_RAW13 = 29
    STIM_RAW14 = 30
    STIM_RAW15 = 31
    STIM_HW = -1


class ITMOpcode(Enum):
    """ Opcodes for ITM frames that are built in ITMFramer """
    SYNCHRONIZATION = 0
    EXTENSION = 1
    OVERFLOW = 2
    TIMESTAMP = 3
    PACKET_PC = 4
    SOURCE_SW = 5
    COUNTER_WRAP = 6
    EXCEPTION = 7
    TRACE = 8
    UNPARSED = None


hwExecfunctDict = {1: "Entered exception indicated by ExceptionNumber field",
                   2: "Exited exception indicated by ExceptionNumber field.",
                   3: "Returned to exception indicated by ExceptionNumber field."}

counterDict = {5: "CPI",
               4: "Exc",
               3: "Sleep",
               2: "LSU",
               1: "Fold",
               0: "Cyc"}

timestampDict = {0xC: "in sync",
                 0xD: "TS delayed",
                 0xE: "packet delayed",
                 0xF: "packet and timestamp delayed"}

accessDict = {5: "at {}, Write Access, comparator: {}, value : 0x{:X} ",
              4: "at {}, Read Access, comparator: {}, value : 0x{:X} ",
              3: "at {}, Address access, comparator: {}, value : 0x{:X} ",
              2: "at {}, PC value Access, comparator: {}, value : 0x{:X} "}


def build_value(buf):
    """Turn an iterable into a little-endian integer"""
    value = 0
    for idx, val in enumerate(buf): value += val << (idx * 8)
    return value


@dataclass
class ITMFrame:
    """Base ITM frame that stores common information and should be subclassed by other frames"""
    header: int
    ts_counter: float = 0
    size: int = 0
    value: int = 0
    string: str = "Frame has not yet been parsed"

    def __len__(self):
        return self.size


@dataclass
class ITMSyncFrame(ITMFrame):
    """ Synchronization Frame"""
    opcode: ITMOpcode = ITMOpcode.SYNCHRONIZATION
    data: list = field(default_factory=list)
    size: int = 0

    """ Synchronization packets are at least 47 bytes of value zero followed by 1 byte of value one """

    def parse(self, buf):
        """Build ITMSyncFrame from buf"""
        # Find index of 1 and add 1 since we want to remove the 1
        idx = buf.index(1) + 1
        # Store data
        self.data = buf[:idx]
        self.size = len(self.data)
        # Remove sync bytes from input data
        return buf[idx:]

    def __str__(self):
        return "ITM Synchronization packet of size {}".format(self.size)


@dataclass
class ITMExtensionFrame(ITMFrame):
    """Extension Frame"""
    opcode: ITMOpcode = ITMOpcode.EXTENSION
    data: list = field(default_factory=list)

    """ Extension packet is continued until most significant bit is 0"""

    def parse(self, buf):
        """Build ITMExtensionFrame from buf"""
        for idx, val in enumerate(buf):
            # Look for most significant bit to be 0
            if val & 0x80 == 0:
                self.size = idx
            else:
                self.data.append(buf[idx])
        return buf[self.size:]

    def __str__(self):
        return "ITM Extension Frame of size {}".format(self.size)


@dataclass
class ITMOverflowFrame(ITMFrame):
    """Overflow frame"""
    opcode: ITMOpcode = ITMOpcode.OVERFLOW

    """ Overflow packet is only one byte """

    def __post_init__(self):
        """Send warning that overflow frame occurred"""
        logger.warning("ITM Frame Overflow")

    def __str__(self):
        return "ITM Overflow packet"


@dataclass
class ITMTimestampFrame(ITMFrame):
    """Timestamp frame for all timestamp variants"""
    opcode: ITMOpcode = ITMOpcode.TIMESTAMP

    """Retrieve and parse an ITM timestamp"""

    def parse(self, buf):
        """Build ITMTimestampFrame from buf"""
        # Find out what type of timestamp this is
        try:
            self.string = timestampDict[self.header >> 4]
        except KeyError:
            self.string = " TS reserved"
            logger.warning("Reserved field used for timestamp")

        # Only build a timestamp if there is a continuation bit
        if (self.header & 0x80) and len(buf) > 0:
            for idx, val in enumerate(buf):
                # Continue adding value, shifting left each time
                self.ts_counter += (val & 0x7F) << (7 * idx)
                if val & 0x80 == 0:
                    # No continuation bit == stop
                    self.size = idx + 1
                    break
            self.string = "TIMESTAMP {}: + {} cycles".format(self.string, self.ts_counter)
        else:
            self.string = "reserved timestamp header {}".format(self.header)
        return buf[self.size:]

    def __str__(self):
        return self.string


@dataclass
class ITMSourceFrame(ITMFrame):
    """Software or hardware source frame. SW / HW frames should subclass this"""
    port: ITMStimulusPort = None

    def __post_init__(self):
        self.port = ITMStimulusPort(self.header >> 3)
        # Get size
        var_len = self.header & 0x03
        if var_len == 3:
            self.size = 4
        else:
            self.size = var_len


@dataclass
class ITMSourceHwPcFrame(ITMSourceFrame):
    """Program Counter Hardware Source Frame"""
    opcode: ITMOpcode = ITMOpcode.PACKET_PC

    def parse(self, buf):
        """Build ITMSourceHwPcFrame from buf"""
        self.value = build_value(buf[:self.size])
        return buf[self.size:]

    def __str__(self):
        if self.size == 4:
            self.string = "Received a PC sample @ {} PC: 0x{:X}".format(self.ts_counter, self.value)
        else:
            self.string = "Received a IDLE PC sample @ {}".format(self.ts_counter)
        return self.string


@dataclass
class ITMSourceHwCntWrapFrame(ITMSourceFrame):
    """Hardware Source Frame indicating which counter(s) have wrapped."""
    opcode: ITMOpcode = ITMOpcode.COUNTER_WRAP

    def parse(self, buf):
        """Build ITMSourceHwCntWrapFrame from buf"""
        # Payload is only one byte
        self.value = buf[0]
        return buf[1:]

    def __str__(self):
        string = "At timestamp {}, the following counter(s) wrapped: ".format(self.ts_counter)
        return string + "".join([counterDict[i] + " " if self.value & (1 << i) else "" for i in counterDict.keys()])


@dataclass
class ITMSourceHwExceptionFrame(ITMSourceFrame):
    """Hardware source frame indicating exceptions such as interrupt entrance / exit"""
    opcode: ITMOpcode = ITMOpcode.EXCEPTION
    num_exception: int = 0
    func_exception: int = 0

    def parse(self, buf):
        """Build ITMSourceHwExceptionFrame from buf"""
        self.num_exception = buf[0] + ((buf[1] & 0x1) << 8)
        self.func_exception = (buf[1] & 0x30) >> 4
        # We used two bytes so discard them now
        return buf[2:]

    def __str__(self):
        return "An Exception has occurred @ {}, Exception Number: {}, Function done: {}".format(
            self.ts_counter, self.num_exception, hwExecfunctDict[self.func_exception])


@dataclass
class ITMSourceHwTraceFrame(ITMSourceFrame):
    """Hardware source frame indicating all possibilities: watchpoints, etc"""
    opcode: ITMOpcode = ITMOpcode.TRACE
    hwPacketType: int = 0
    dataTracePacketType: int = 0
    comparator: int = 0
    direction: int = 0

    def __post_init__(self):
        """Extract information from hardware packet type"""
        self.dataTracePacketType = self.hwPacketType >> 3
        self.comparator = (self.hwPacketType >> 1) & 0x3
        self.direction = self.hwPacketType & 0x1
        self.accessType = self.direction + (self.dataTracePacketType << 1)
        super().__post_init__()

    def parse(self, buf):
        """Build ITMSourceHwTraceFrame from buf"""
        self.value = build_value(buf[:self.size])
        return buf[self.size:]

    def __str__(self):
        return "HW Trace " + accessDict[self.accessType].format(self.ts_counter / 1000, self.comparator, self.value)


@dataclass
class ITMSourceSWFrame(ITMSourceFrame):
    """Software source frame"""
    opcode: ITMOpcode = ITMOpcode.SOURCE_SW
    data: list = field(default_factory=list)

    def parse(self, buf):
        """Build ITMSourceSWFrame from buf"""
        # Store data
        self.data = buf[:self.size]
        # build string
        self.string = "SW SWIT at +{}, port {}: {}".format(
            self.ts_counter, self.port.name, " ".join((("0x{:02X}".format(i)) for i in self.data)))
        return buf[self.size:]

    def __str__(self):
        return self.string


class ITMFramer:
    """
    Manages parsing serial data into ITMFrames and outputs ITMFrames onto output queue q

    Args:
        q: Output queue

    """

    def __init__(self, q):
        # Set up logging
        logger.addFilter(LoggingFilter())
        # Create the PDU stream thread.
        self._out_q = q
        self._first_read = True
        self.last_ts_counter = 0
        logger.critical("ITM Framer initialized. Must receive Reset Frame to start parsing")

    def parse(self, buf=None):
        """
        Parse all of an input byte buffer into ITMFrames until the buffer size is <= MAX_ITM_FRAME_SIZE

        There is special funcionality to handle the reset frame (indentified by ITM_RESET_TOKEN). Initially,
        parsing of other frames will not start until the reset frame is found. After this, the buffer received for
        parsing will be searched for the reset frame. If the reset frame is found, all preceding data will be discarded
        and parsing will continue at the  software source frame containing the rest

        Args:
          buf: input buffer to parse (Default value = None)

        Returns:
            Unparsed portion of the input buffer

        """
        if len(buf) is 0: return buf

        # Return full buffer in case any part of the rest token was at the end, in
        # which case only part of the token may have been received. Then reparse
        # the next time data is added to the buffer
        if buf[-1] is 0xBB or buf[-1] is 0xC0:
            return buf
        # If the reset token is found
        elif ITM_RESET_TOKEN in buf:
            # Discard anything before the reset token
            buf = buf[buf.index(ITM_RESET_TOKEN):]
        # If first run and no reset found yet, don't parse anything
        elif self._first_read is True:
            logger.debug("Waiting for a reset frame to begin parsing.")
            return bytearray()

        # While there is a full packet to parse...
        while len(buf) > MAX_ITM_FRAME_SIZE:
            # If this was the first time, clear this flag
            if self._first_read: self._first_read = False
            # Read the header byte
            header = buf.pop(0)

            # Figure out what type of packet this is
            # Synchronization packet is all zeros
            if header == 0x00:
                frame = ITMSyncFrame(0)
            else:
                # Everything besides source packets have the 2 least significant bits set to 0
                if (header & 0x03) == 0x00:
                    # Header == Overflow
                    if header == HDR_OVERFLOW:
                        frame = ITMOverflowFrame(header)
                    # Least significant byte of header Header == 0 --> Local timestamp
                    elif (header & 0x0F) == 0x00:
                        frame = ITMTimestampFrame(header)
                    # Least significant byte of header with S bit masked out == Extension
                    elif (header & 0x0B) == 0x08:
                        frame = ITMExtensionFrame(header)
                # Source packets have non-zero least significant bits
                else:
                    # 3rd bit == 0 --> Software Source
                    if (header & 0x04) == 0x00:
                        frame = ITMSourceSWFrame(header, ts_counter=self.last_ts_counter)
                    # 3rd bit == 1 --> Hardware Source
                    else:
                        # Get packet type discriminator ID
                        hw_packet_type = header >> 3
                        # This is a counter Wrap
                        if hw_packet_type == 0x00:
                            frame = ITMSourceHwCntWrapFrame(header, ts_counter=self.last_ts_counter)
                        # This is an exception event
                        elif hw_packet_type == 0x01:
                            frame = ITMSourceHwExceptionFrame(header, ts_counter=self.last_ts_counter)
                        # This is a PC sampling event
                        elif hw_packet_type == 0x02:
                            frame = ITMSourceHwPcFrame(header, ts_counter=self.last_ts_counter)
                        # This is a hardware trace packet
                        elif hw_packet_type <= 0x17:
                            frame = ITMSourceHwTraceFrame(header, hwPacketType=hw_packet_type,
                                                          ts_counter=self.last_ts_counter)
                        # Anything else is invalid
                        else:
                            logger.error("Invalid ITM Hardware Source Packet")

            # Parse packet based on packet type
            try:
                if frame.opcode is not ITMOpcode.OVERFLOW:
                    # Parse buffer
                    buf = frame.parse(buf)
                    # Update timestamp if needed
                    if frame.opcode == ITMOpcode.TIMESTAMP: self.last_ts_counter = frame.ts_counter
                    # Log packet that was just parsed
                    logger.debug("%s" % frame)
                    # queue packet for output
                    self._out_q.put(frame)
            except Exception as e:
                logger.error("Invalid ITM Packet")
                logger.debug(e)

        # Return unparsed data
        return buf
