import sys
import os
import enum
from dataclasses import *
from swo.swo_framer import *
from wireshark_output.wireshark_output import *
from trace_db.trace_db import TraceDB
import struct
import logging
from construct import *

logger = logging.getLogger("TIRTOS Framer")


@dataclass
class TIRTOSBase(FrameBase):
    swo_frame: SWOFrame = None
    wireshark_out: list = None

    def __post_init__(self):
        self.rat_ts_s = self.swo_frame.rat_ts_s
        self.rtc_ts_s = self.swo_frame.rtc_ts_s
        self.opcode = self.swo_frame.opcode
        self.file = self.swo_frame.file
        self.line = self.swo_frame.line
        self.level = self.swo_frame.level
        self.module = self.swo_frame.module

        # Construct base WS output
        self.wireshark_out = self.swo_frame.wireshark_out + [
            WSOutputElement(Protofields.COMMON_OPEN_TREE, "TI-RTOS Kernel Logging")]

    def __str__(self):
        return "RAT: {:.7f} s, RTC: {:.7f} : {} --> ".format(self.rat_ts_s, self.rtc_ts_s, self.file)


@dataclass
class TIRTOSLog(TIRTOSBase):
    traceDB: TraceDB = None

    def __post_init__(self):
        super().__post_init__()
        arg_list = []
        level = "CUSTOM"
        # Take copy of the frame buf
        tmp_buf = self.swo_frame.buf.copy()
        # Extract log level
        log_level = tmp_buf.pop(0)
        # pop remaining "unused" bytes
        tmp_buf.pop(0)  # Contains the number of args sent
        tmp_buf.pop(0)
        tmp_buf.pop(0)

        # Assume text is not loaded in the kernel, set default formats for INFO, WARNING and ERROR
        if log_level == 1:  # If INFO
            level = "INFO"
            format_string = "INFO: (%s:%d) %s"
        elif log_level == 2:  # If WARNING
            level = "WARNING"
            format_string = "WARNING: (%s:%d) %s"
        elif log_level == 4:  # If ERROR
            level = "ERROR"
            format_string = "ERROR: (%s:%d) %s"

        # Check if text was loaded (address != 0) and replace the format if this is the case
        format_addr = tmp_buf.pop(0) + (tmp_buf.pop(0) << 8) + (tmp_buf.pop(0) << 16) + (tmp_buf.pop(0) << 24)
        if format_addr:
            # Get format string (remove fancy pancy %$S and %$F from sysbios)
            format_string = self.traceDB.get_string_from_address(format_addr)
            format_string = format_string.decode('utf-8').replace("%$S", "%s")
            format_string = format_string.replace("%$F", "%s:%d, ")

        # If a Log INFO, WARNING or ERROR event, format the initial string
        if level != "CUSTOM":
            format_addr = tmp_buf.pop(0) + (tmp_buf.pop(0) << 8) + (tmp_buf.pop(0) << 16) + (tmp_buf.pop(0) << 24)
            file = self.traceDB.get_string_from_address(format_addr).decode('utf-8')
            line = tmp_buf.pop(0) + (tmp_buf.pop(0) << 8) + (tmp_buf.pop(0) << 16) + (tmp_buf.pop(0) << 24)
            format_addr = tmp_buf.pop(0) + (tmp_buf.pop(0) << 8) + (tmp_buf.pop(0) << 16) + (tmp_buf.pop(0) << 24)
            sec_format = self.traceDB.get_string_from_address(format_addr).decode('utf-8')

        # Put the rest of the arguments in the argument list
        while len(tmp_buf):
            arg_list.append(tmp_buf.pop(0) + (tmp_buf.pop(0) << 8) + (tmp_buf.pop(0) << 16) + (
                    tmp_buf.pop(0) << 24))

        # Print the rest of the arguments as suggested by the new format string. Start with adding
        # "Raw" prints if needed (number of % is less then the number of args).
        dif = len(arg_list) - sec_format.count("%")
        if dif < 0:
            # There is less arguments then specifiers for some reason, handle this gracefully
            sec_format = sec_format.replace("%", "$")
            sec_format = (sec_format + " [NOT ENOUGH ARGUMENTS TO FORMAT THE STRING]")

        temp_args = []
        last_offset = 0
        i = 0
        # Iterate over the specifiers to see if we need to fetch any strings
        while (i < len(arg_list)) and not (dif < 0):
            last_offset = sec_format.find("%", last_offset) + 1
            if last_offset:
                # Are we out of specifiers?
                if i > sec_format.count("%"):
                    sec_format.replace("%", "$")
                else:
                    # Is it a string format?
                    if sec_format[last_offset] == "s":
                        temp_string = self.traceDB.get_string_from_address(arg_list[i]).decode('utf-8')
                        temp_args.append(temp_string)
                    else:
                        temp_args.append(arg_list[i])
            i += 1

        # Complete the formatted string
        sec_format = (sec_format % tuple(temp_args))
        format_string = format_string % (file, line, sec_format)

        # Construct the WS output
        self.wireshark_out += [WSOutputElement(Protofields.COMMON_INFO, format_string)]
        self.wireshark_out += [WSOutputElement(Protofields.TIRTOS_LOG_EVENT, level)]

        if level != "CUSTOM":
            # For INFO, WARNING and ERROR, the three first arguments is file, line, func. Display this nicely
            self.wireshark_out += [WSOutputElement(Protofields.TIRTOS_LOG_FILE, file)]
            self.wireshark_out += [WSOutputElement(Protofields.TIRTOS_LOG_LINE, line)]
            self.wireshark_out += [
                WSOutputElement(Protofields.COMMON_CUSTOM, "Formatted string", sec_format)]

        # List all arguments
        arg_num = 0
        i = 0
        if i < len(arg_list):
            self.wireshark_out += [WSOutputElement(Protofields.COMMON_OPEN_TREE, "Arguments")]
            while i < len(arg_list):
                self.wireshark_out += [
                    WSOutputElement(Protofields.COMMON_CUSTOM, "Arg {}".format(arg_num), str(arg_list[i]))]
                i += 1
                arg_num += 1
            self.wireshark_out += [WSOutputElement(Protofields.COMMON_CLOSE_TREE)]


@dataclass
class TIRTOSHeapTrack(TIRTOSBase):
    traceDB: TraceDB = None
    heapTrack: dict = field(default_factory=dict)

    def __post_init__(self):
        super().__post_init__()
        lr = self.swo_frame.values[0]
        memory_address = self.swo_frame.values[1]
        # Get the origin function, file and line using the "lr" argument
        fxn, file, line = self.traceDB.get_info_for_address(lr)
        if "malloc" in self.swo_frame.event:
            memory_size = self.swo_frame.values[2]
            info_string = "Failed to allocate %d bytes inside %s:%d (%s)" % (memory_size, fxn, line, file)
            event = "Memory allocation"
            # Did it succeed?
            if memory_address > 0:
                # Store in dict
                self.heapTrack[memory_address] = [fxn.decode("utf-8"), file.decode("utf-8"), line, memory_size]
                info_string = "%d bytes was allocated (0x%8x) inside %s:%d (%s)" % (
                memory_size, memory_address, fxn, line, file)
        else:
            event = "Memory deallocation"
            if self.heapTrack[memory_address] is not None:
                org_fxn, org_file, org_line, memory_size = self.heapTrack[memory_address];
                info_string = "%d (0x%8x) bytes was freed inside %s:%d (%s), allocated inside %s:%d (%s)" % (
                memory_size, memory_address, fxn, line, file, org_fxn, org_line, org_file)
                # Remove from dict
                self.heapTrack.pop(memory_address, None)
            else:
                info_string = "Freeing un-tracked memory inside %s:%d (%s)"

        # Populate protofields
        self.wireshark_out += [WSOutputElement(Protofields.TIRTOS_LOG_EVENT, event)]
        self.wireshark_out += [WSOutputElement(Protofields.TIRTOS_LOG_FILE, file)]
        self.wireshark_out += [WSOutputElement(Protofields.TIRTOS_LOG_LINE, line)]
        self.wireshark_out += [WSOutputElement(Protofields.COMMON_INFO, info_string)]
        # Custom protofields
        self.wireshark_out += [
            WSOutputElement(Protofields.COMMON_CUSTOM, "Function", fxn.decode("utf-8"))]
        self.wireshark_out += [
            WSOutputElement(Protofields.COMMON_CUSTOM, "Info", info_string)]
        # Print current heap list
        if len(self.heapTrack) > 0:
            self.wireshark_out += [WSOutputElement(Protofields.COMMON_OPEN_TREE, "Tracked heap usage")]
            for key, val in self.heapTrack.items():
                string = "0x%8x, allocated in %s:%d (%s)" % (key, val[0], val[2], val[1])
                self.wireshark_out += [WSOutputElement(Protofields.COMMON_CUSTOM, string, str(val[3]))]
            self.wireshark_out += [WSOutputElement(Protofields.COMMON_CLOSE_TREE)]


class TIRTOSFramer:
    def __init__(self, db):
        self._traceDB = db
        self._heapTrack = {}
        pass

    def reset(self):
        self._heapTrack = {}

    def parse(self, swo_frame=None):
        tirtos_frame = None
        # Re-construct the TI-RTOS Log structure
        try:
            if swo_frame.opcode == SWOOpcode.BUFFER:
                tirtos_frame = TIRTOSLog(swo_frame=swo_frame, traceDB=self._traceDB)
            elif (swo_frame.opcode == SWOOpcode.EVENT) and \
                    ((swo_frame.event == "SWOWrapper_malloc") or (swo_frame.event == "SWOWrapper_free")):
                tirtos_frame = TIRTOSHeapTrack(swo_frame=swo_frame, traceDB=self._traceDB, heapTrack=self._heapTrack)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error(exc_type, fname, exc_tb.tb_lineno)
        finally:
            if tirtos_frame is not None: self.completed(tirtos_frame)
            return tirtos_frame

    def completed(self, frame=None):
        # Finish building wireshark output
        # close tree
        frame.wireshark_out += [WSOutputElement(Protofields.COMMON_CLOSE_TREE)]
        pass
