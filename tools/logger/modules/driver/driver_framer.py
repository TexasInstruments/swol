import sys
import os
import enum
from dataclasses import *
from swo.swo_framer import *
from wireshark_output.wireshark_output import *
from trace_db.trace_db import *
import logging

logger = logging.getLogger("Driver Framer")

driver_map = {
    # Power driver
    "PowerCC26X": "Power Driver",
    "UARTCC26X": "UART Driver",
    "RFCC26X": "RF Driver",
}

reset_constraints = {
    0: [0, {}],
    1: [0, {}],
    2: [0, {}],
    3: [0, {}],
    4: [0, {}],
    5: [0, {}],
    6: [0, {}]
}

constraint_to_string = {
    0: "PowerCC26XX_RETAIN_VIMS_CACHE_IN_STANDBY",
    1: "PowerCC26XX_DISALLOW_SHUTDOWN",
    2: "PowerCC26XX_DISALLOW_STANDBY",
    3: "PowerCC26XX_DISALLOW_IDLE",
    4: "PowerCC26XX_NEED_FLASH_IN_IDLE",
    5: "PowerCC26XX_SWITCH_XOSC_HF_MANUALLY",
    6: "PowerCC26XX_DISALLOW_XOSC_HF_SWITCHING"
}


@dataclass
class DriverStatus(enum.Enum):
    OK = "Ok"
    ERROR = "Error"
    POSSIBLE_ERROR = "Possible Error"


@dataclass
class DriverEvent(FrameBase):
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
        self.status = DriverStatus.OK.value
        self.driver = ""
        for key in driver_map:
            if key in self.file:
                self.driver = driver_map[key]
                break

    def __str__(self):
        return "RAT: {:.7f} s, RTC: {:.7f} : {} --> ".format(self.rat_ts_s, self.rtc_ts_s, self.file)


@dataclass
class PowerEvent(DriverEvent):
    constraints: dict = field(default_factory=dict)
    traceDB: TraceDB = None

    def __post_init__(self):
        super().__post_init__()
        self.info_string = ""
        file = ""
        line = ""
        fxn = ""
        # If the event is a power constraint event
        if str("Power constraint event") == self.swo_frame.string:
            # Get the origin function, file and line using the "lr" argument
            fxn, file, line = self.traceDB.get_info_for_address(self.swo_frame.values[1])
            # Store total count as well as incrementing the individual file count
            self.constraints[self.swo_frame.values[3]][0] = self.swo_frame.values[2]
            # If first value is 1 it is a set event, else release
            if self.swo_frame.values[0]:
                # Increment file counter
                if file in self.constraints[self.swo_frame.values[3]][1]:
                    self.constraints[self.swo_frame.values[3]][1][file] += 1
                else:
                    self.constraints[self.swo_frame.values[3]][1][file] = 1
                # Info string
                self.info_string = (constraint_to_string[self.swo_frame.values[3]] + "'" +
                                    " constraint was set inside %s by %s:%d.") % (
                                   file.decode("utf-8"), fxn.decode("utf-8"), line)
            else:
                # Decrement file counter
                if file in self.constraints[self.swo_frame.values[3]][1]:
                    self.constraints[self.swo_frame.values[3]][1][file] -= 1
                else:
                    # If the file is not inside the dict (for some reason), add a dummy entry with 0 count
                    self.constraints[self.swo_frame.values[3]][1][file] = 0
                # Info string
                self.info_string = (constraint_to_string[self.swo_frame.values[3]] + "'" +
                                    " constraint was released inside {} by {}:{}.").format(file.decode("utf-8"),
                                                                                           fxn.decode("utf-8"), line)
        # Construct WS output
        # TODO: Remove this sepreator from wireshark output
        self.wireshark_out = [WSOutputElement(Protofields.COMMON_CUSTOM,
                                              ": ========================" + \
                                              " Power Constraint Event " + \
                                              "========================"
                                              , "")]
        # Which constraint is set/released
        self.wireshark_out += [
            WSOutputElement(Protofields.DRIVER_POWER_CONSTRAINT, constraint_to_string[self.swo_frame.values[3]])]
        # From which file does the action relate to ...
        if self.swo_frame.values[0]:
            self.wireshark_out += [
                WSOutputElement(Protofields.COMMON_CUSTOM, "Set in file", file.decode("utf-8"))]
        else:
            self.wireshark_out += [
                WSOutputElement(Protofields.COMMON_CUSTOM, "Released in file", file.decode("utf-8"))]
        # ... and at which line
        self.wireshark_out += [WSOutputElement(Protofields.COMMON_CUSTOM, "Line", str(line))]

        # If there is active power constraints, add these as part of the WS output
        if len(self.constraints):
            # Open tree (level 1)
            self.wireshark_out += [WSOutputElement(Protofields.COMMON_OPEN_TREE, "Active power constraints")]
            for key, val in self.constraints.items():
                if val[0]:
                    # Open tree (level 2)
                    self.wireshark_out += [WSOutputElement(Protofields.COMMON_OPEN_TREE, constraint_to_string[key])]
                    counter = 0
                    # For each constraint, list each file holding constraints
                    for file, count in val[1].items():
                        counter = counter + count
                        if count != 0:
                            tmp = file.decode("utf-8")
                            # If the count is negative, the software could be having a bug, provide some printout on this
                            if count < 0:
                                tmp += " [Negative count, possible software bug!]"
                                self.status = DriverStatus.POSSIBLE_ERROR.value
                            self.wireshark_out += [WSOutputElement(Protofields.COMMON_CUSTOM, tmp, str(count))]

                    # If list happens to be empty but there is constraint or if there is constraints that is unaccounted for
                    if (counter < val[0]) and (counter > -1):
                        dif = val[0] - counter
                        self.wireshark_out += [
                            WSOutputElement(Protofields.COMMON_CUSTOM, "[Unknown source(s)]", str(dif))]
                    # Close tree (level 2)
                    self.wireshark_out += [WSOutputElement(Protofields.COMMON_CLOSE_TREE)]
            # Close tree (level 1)
            self.wireshark_out += [WSOutputElement(Protofields.COMMON_CLOSE_TREE)]

    def __str__(self):
        return self.info_string


class DriverFramer(FramerBase):
    def __init__(self, db):
        self._constraints = reset_constraints
        self._traceDB = db

    def reset(self):
        self._constraints = reset_constraints

    def parse(self, swo_frame=None):
        driver_frame = None
        try:
            # Is this an Power driver Event?
            if swo_frame.opcode == SWOOpcode.EVENT and ("PowerCC26X" in swo_frame.file):
                driver_frame = PowerEvent(swo_frame=swo_frame, constraints=self._constraints, traceDB=self._traceDB)
        except Exception as e:
            logger.error(e)
        finally:
            if driver_frame is not None:
                self.completed(driver_frame)
            # This frame was not parsed. The same input SWO frame will be returned
            else:
                return swo_frame
            return driver_frame

    def completed(self, frame=None):
        # Finish building wireshark output
        # Append open tree and decoded driver after SWO output
        frame.wireshark_out = frame.swo_frame.wireshark_out + \
                              [WSOutputElement(Protofields.COMMON_OPEN_TREE, "Driver Logger Frame")] + \
                              [WSOutputElement(Protofields.DRIVER_FILE, frame.driver)] + \
                              [WSOutputElement(Protofields.DRIVER_STATUS, frame.status)] + \
                              frame.wireshark_out + \
                              [WSOutputElement(Protofields.COMMON_INFO, str(frame))] + \
                              [WSOutputElement(Protofields.COMMON_CLOSE_TREE)]
