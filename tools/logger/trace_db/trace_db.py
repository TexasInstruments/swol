from elftools.dwarf.descriptions import describe_form_class
from elftools.elf.elffile import ELFFile
import os
import logging
import pickle
import hashlib
import json
from appdirs import AppDirs
from swo.swo_framer import SWOOpcode

# String to opcode dictionary
swo_string_to_opcode = {
    "SWO_OPCODE_FORMATED_TEXT": SWOOpcode.FORMATTED_TEXT,
    "SWO_OPCODE_EVENT": SWOOpcode.EVENT,
    "SWO_OPCODE_EVENT_SET_START": SWOOpcode.EVENT_SET_START,
    "SWO_OPCODE_EVENT_SET_END": SWOOpcode.EVENT_SET_END,
    "SWO_OPCODE_BUFFER": SWOOpcode.BUFFER,
    "SWO_OPCODE_IDLE_BUFFER_OVERFLOW": SWOOpcode.BUFFER_OVERFLOW,
    "SWO_OPCODE_WATCHPOINT": SWOOpcode.WATCHPOINT,
    "SWO_OPCODE_SYNC_TIME": SWOOpcode.SYNC_TIME,
    "SWO_EVENT_CREATION": SWOOpcode.EVENT_CREATION
}

# Set up logger
logger = logging.getLogger("TraceDB")

# Base address of trace sections
TRACE_BASE_ADDR = 0x60000000
TRACE_SECTION_NAME = ".swo_trace"


class ElfString:
    def __init__(self, value):
        # Get opcode and strip from value
        self.opcode, value = value.split(":::", 1)
        self.opcode = swo_string_to_opcode[self.opcode]

        # Parse remainder of string if it is an event creation
        if self.opcode is SWOOpcode.EVENT_CREATION:
            _, _, self.file, self.line, self.event, self.logModule, self.string, _ = value.split(":::")
        else:
            self.value = value


class TraceDB:
    def __init__(self, elf, sdk_path=""):
        self.elf = elf
        self.sdk_path = sdk_path
        self.device = ""
        self.rom_sub_path = ""
        self.traceDB = {}
        self.eventDB = {}
        self.functionDB = {}

        # Set app directories
        dirs = AppDirs("logger", "swol")
        if not os.path.exists(dirs.user_data_dir):
            os.makedirs(dirs.user_data_dir)
        trace_db_pickle_file = os.path.join(os.path.dirname(os.path.realpath(dirs.user_data_dir)), "trace_db.pkl")
        func_db_pickle_file = os.path.join(os.path.dirname(os.path.realpath(dirs.user_data_dir)), "func_db.pkl")
        event_db_pickle_file = os.path.join(os.path.dirname(os.path.realpath(dirs.user_data_dir)), "event_db.pkl")
        json_file = os.path.join(os.path.dirname(os.path.realpath(dirs.user_data_dir)), "trace_db.json")

        build_trace_db = True
        build_func_db = False if self.sdk_path is "" else True
        # Build current hash
        hasher = hashlib.md5()
        try:
            with open(self.elf, 'rb') as f:
                hasher.update(f.read())
        except Exception as e:  # most likely file not found if path to SWO is invalid
            logger.error("Not able to open elf file " + self.elf)
            raise e

        current_hash = hasher.hexdigest()
        json_dict = {}

        try:
            # Read json data
            with open(json_file, 'rb') as f:
                json_dict = json.load(f)
            try:
                # Get hash of stored elf file
                last_hash = json_dict["hash"]
                # See whether hash's match
                if current_hash == last_hash:
                    build_trace_db = False
            except KeyError:
                logging.error("No previous hash found")
            # See if SDK path changed
            if build_func_db is True:
                try:
                    last_sdk_path = json_dict["sdk"]
                    if self.sdk_path == last_sdk_path:
                        build_func_db = False
                except KeyError:
                    logger.error("No SDK path in JSON file")
        except (json.JSONDecodeError, FileNotFoundError):
            logger.error("Can't open JSON file @ " + json_file)

        # Build and pickle databases if needed
        if build_trace_db is True or build_func_db is True:
            # Build elf information
            self.get_elf_db()
            # Pickle trace database
            with open(trace_db_pickle_file, "wb") as f:
                pickle.dump(self.traceDB, f)
            # Pickle event database
            with open(event_db_pickle_file, "wb") as f:
                pickle.dump(self.eventDB, f)
            # Store elf hash to json file
            json_dict["hash"] = current_hash
            with open(json_file, 'w') as f:
                json.dump(json_dict, f)
            logger.critical("TraceDB and EventDB have been pickled")
            # Build SDK path information
            self.get_rom_symbols()
            # Pickle database
            with open(func_db_pickle_file, "wb") as f:
                pickle.dump(self.functionDB, f)
            # Store sdk path to json file
            json_dict["sdk"] = self.sdk_path
            with open(json_file, 'w') as f:
                json.dump(json_dict, f)
            logger.critical("FuncDB has been pickled")
        elif build_trace_db is False and build_func_db is False:
            # Load from pickled trace file
            try:
                with open(trace_db_pickle_file, 'rb') as f:
                    self.traceDB = pickle.load(f)
                with open(event_db_pickle_file, 'rb') as f:
                    self.eventDB = pickle.load(f)
                logger.critical("Pickled trace and event databases successfully loaded")
            except FileNotFoundError:
                logger.error("Pickled trace_db or event_db file not found")
            # Load from pickled func db file
            try:
                with open(func_db_pickle_file, 'rb') as f:
                    self.functionDB = pickle.load(f)
                logger.critical("Pickled function database successfully loaded")
            except FileNotFoundError:
                logger.error("Pickled trace_db file not found")
        logger.critical("Done configuring databases")

    # Return function, file and line based on a address
    def get_info_for_address(self, addr):
        for key in self.functionDB:
            if addr in range(key[0], key[1]):
                return self.functionDB[key]
        # If not in our data base (ROM for example)
        return b'<Function not in dict>', b'<Unknown>', 0

    def get_string_from_address(self, addr):
        if self.elf != "":
            with open(self.elf, 'rb') as f:
                # Create ELF file object
                elffile = ELFFile(f)
                # Get debug info (needed to populate elf?)
                elffile.get_dwarf_info()
                # Find relevant section
                for key, val in elffile._section_name_map.items():
                    section = elffile.get_section(val)
                    if addr in range(section.header['sh_offset'],
                                     section.header['sh_offset'] + section.header['sh_size']):
                        # Move to the beginning of the string in the strea
                        section.stream.seek(4 + elffile.header['e_ehsize'] + addr)
                        # Read out chunks off 100, looking for NULL
                        string = section.stream.read(100)
                        while 0 not in string:
                            string += section.stream.read(100)
                        # Strip string at NULL
                        return string.split(b'\x00')[0]

    def get_rom_symbols(self):
        if self.sdk_path != "":
            # Search through folders to figure out device and ROM sub path
            with os.scandir(self.sdk_path) as listOfEntries:
                for entry in listOfEntries:
                    # Get chip family based of SDK file names
                    if "cc13x2_26x2" in entry.name:
                        self.device = "cc13x2_cc26x2"
                        self.rom_sub_path = os.path.join("cc26xx", "cc26x2v2", "golden", "CC26xx", "rtos_rom.txt")
                        break
                    elif "cc13x0" in self.sdk_path:
                        self.device = "cc13x0"
                        self.rom_sub_path = os.path.join("cc13xx", "golden", "CC13xx", "rtos_rom.txt")
                        break
                    elif "cc2640r2" in self.sdk_path:
                        self.device = "cc2640r2"
                        self.rom_sub_path = os.path.join("cc26xx", "r2", "golden", "CC26xx", "rtos_rom.txt")
                        break

                if self.device == "":
                    logger.warning(f"Unknown device at path: {self.sdk_path}")
                    return

            logger.critical("Adding symbols for the " + self.device + " SDK")
            self.get_tirtos_symbols()
            self.get_driverlib_symbols()
            self.get_ble_symbols()

    def get_tirtos_symbols(self):
        logger.debug("TIRTOS SYMBOLS =======================================================")
        # Get path to TI-RTOS symbols
        tirtos_rom_path = os.path.join(self.sdk_path, "kernel", "tirtos", "packages", "ti", "sysbios",
                                       "rom", "cortexm", self.rom_sub_path)
        # Store TI-RTOS symbols to functionDB
        with open(tirtos_rom_path, 'rb') as f:
            logger.critical("Adding TI-RTOS ROM symbols to the function dictionary...")
            content = f.readlines()
            for x in content[3:]:
                x = x.rstrip()  # Remove trailing whitespace
                if x:
                    x = x.split()
                    lowpc = int(x[0].decode('utf-8'), 0)
                    highpc = lowpc + int(x[1].decode('utf-8'), 0)
                    fxn_name = x[2]
                    # Add to functionDB
                    self.functionDB[(lowpc, highpc)] = [fxn_name, b'<In ROM>', 0]
                    # Print for debugging
                    logger.debug("{}() @ {}:{}".format(fxn_name.decode("utf-8"), b'<In ROM>'.decode("utf-8"), 0))
                else:
                    break

    def add_to_funcdb(self, elf_file):
        # Create ELF file object
        elf = ELFFile(elf_file)
        # Get debug info
        dwarf_info = elf.get_dwarf_info()
        # Go over all compiler units (CU)
        for CU in dwarf_info.iter_CUs():
            # Go over all debug information entries (DIE) in given CU
            for DIE in CU.iter_DIEs():
                # We only care about subprogram
                if DIE.tag == 'DW_TAG_subprogram':
                    if DIE.attributes.get('DW_AT_low_pc', None) is not None:
                        low_pc = DIE.attributes['DW_AT_low_pc'].value
                        if DIE.attributes.get('DW_AT_name', None) is not None:
                            fxn_name = DIE.attributes['DW_AT_name'].value
                            # DWARF v4 in section 2.17 describes how to interpret the
                            # DW_AT_high_pc attribute based on the class of its form.
                            # For class 'address' it's taken as an absolute address
                            # (similarly to DW_AT_low_pc); for class 'constant', it's
                            # an offset from DW_AT_low_pc.
                            high_pc_attr = DIE.attributes['DW_AT_high_pc']
                            high_pc_attr_class = describe_form_class(high_pc_attr.form)
                            if high_pc_attr_class == 'address':
                                high_pc = high_pc_attr.value
                            elif high_pc_attr_class == 'constant':
                                high_pc = low_pc + high_pc_attr.value
                            else:
                                logger.error('Error: invalid DW_AT_high_pc class:', high_pc_attr_class)
                                continue

                            # Get file
                            try:
                                file_index = DIE.attributes['DW_AT_decl_file'].value
                            except KeyError:
                                continue
                            else:
                                line_prog = dwarf_info.line_program_for_CU(CU)
                                file = line_prog['file_entry'][file_index - 1].name
                                # Get line
                                line = DIE.attributes['DW_AT_decl_line'].value
                                # Add to functionDB
                                self.functionDB[(low_pc, high_pc)] = [fxn_name, file, line]
                                # Print for debugging
                                logger.debug(
                                    "{}() @ {}:{}".format(fxn_name.decode("utf-8"), file.decode("utf-8"), line))

    def get_driverlib_symbols(self):
        logger.debug("DRIVERLIB SYMBOLS =======================================================")
        # The cc2640r2 path is different for driverlib
        temp_device = "cc26x0r2" if self.device == "cc2640r2" else self.device
        # Get driverlib ROM symbols
        driverlib_rom_path = os.path.join(self.sdk_path, "source", "ti", "devices", temp_device,
                                          "rom", "driverlib.elf")
        with open(driverlib_rom_path, 'rb') as f:
            logger.critical("Adding DriverLib ROM symbols to the function dictionary...")
            self.add_to_funcdb(f)

    def get_ble_symbols(self):
        logger.debug("BLE ROM SYMBOLS =======================================================")
        if self.device == "cc13x2_cc26x2" or self.device == "cc2640r2":
            ble_rom_path = os.path.join(self.sdk_path, "source", "ti", "ble5stack", "rom", "ble_rom_releases")
            if self.device == "cc13x2_cc26x2":
                ble_rom_path = os.path.join(ble_rom_path, "cc26x2_v2_pg2", "Final_Release", "ble_rom.out")
            elif self.device == "cc2640r2":
                ble_rom_path = os.path.join(ble_rom_path, "cc26xx_r2", "Final_Release", "ble_r2.out")
            with open(ble_rom_path, 'rb') as f:
                logger.critical("Adding BLE ROM symbols to the function dictionary...")
                self.add_to_funcdb(f)

    def get_elf_db(self):
        with open(self.elf, 'rb') as f:
            self.get_swo_db(f)
            logger.debug("ELF FILE =======================================================")
            self.add_to_funcdb(f)

    def get_swo_db(self, f):
        elf = ELFFile(f)
        # Find SWO section
        trace_sec = None
        for secnum, sec in enumerate(elf.iter_sections()):
            if TRACE_SECTION_NAME in sec.name:
                trace_sec = elf.get_section(secnum)
                break
        if trace_sec is None:
            raise ValueError("Trace sections not found in elf file. Ensure that the linker file is correct and that "
                             "there is at least one module and level enabled.")
        logger.critical("Creating dictionary of strings and functions from elf file...")
        logger.debug("SWO TRACE =======================================================")
        # Build SWO trace database by searching in symbol table
        for sym in elf.get_section_by_name('.symtab').iter_symbols():
            if sym.entry.st_value & TRACE_BASE_ADDR == TRACE_BASE_ADDR and "SWOSymbol" in sym.name:
                # Find offset into section by subtracting section base address
                offset = trace_sec.header['sh_offset'] + (sym.entry.st_value - TRACE_BASE_ADDR)
                # Seek to offset in ELF
                trace_sec.stream.seek(offset)
                # Read until end of section
                value = trace_sec.stream.read(trace_sec.header['sh_size'] - (
                        offset - trace_sec.header['sh_offset']))
                # Truncate output at null character and remove quotes
                value = value.decode("utf-8").split("\0")[0].replace("\"", "")
                # Create new ElfString to store in dictionary
                elf_string = ElfString(value)
                # Add to relevant database
                if elf_string.opcode is SWOOpcode.EVENT_CREATION:
                    self.eventDB[elf_string.logModule + elf_string.event] = elf_string
                else:
                    self.traceDB[sym.entry.st_value] = elf_string
                logger.debug("{} --> {}".format(hex(sym.entry.st_value), value))

    def get_elf_string(self, addr_offset):
        return self.traceDB[hex(TRACE_BASE_ADDR + addr_offset)]
