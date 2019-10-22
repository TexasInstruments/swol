
#!/usr/bin/env python

# Copyright (c) 2018 Texas Instruments Incorporated. All rights reserved.
#
# Log serial port and parse received ITM frames
#####################################################################################

import sys
import os
import logging
import argparse
import time
import queue
import uuid

from serial_rx import SerialRx
from swo import SWOFramer, SWOOpcode
from itm import ITMFramer, MAX_ITM_FRAME_SIZE
from trace_db import TraceDB
from wireshark_output import gandelf_send_data, gandelf_send_message, pipe_open, pipe_close

# Module Parsers
from modules import BLEFramer
from modules import DriverFramer
#from modules import TIRTOSFramer

######################################################
# MAIN  ##################
if __name__ == '__main__':
    assert sys.version_info >= (3, 7)
    """ This is the Main Function """
    parser = argparse.ArgumentParser(
        description='Used to log serial port and parse received ITM frames into SWO frames.')
    parser.add_argument("port",
                        help="Com port to open. for win: COM54, for mac: /dev/tty.usbmodemXXX")
    parser.add_argument("elf",
                        help="Elf file where the trace strings need to be extracted from")
    parser.add_argument("-s", "--sdk_path",
                        default="",
                        help="Path to the SDK. Used to pick up ROM symbols. Example: C:\ti\simplelink_cc13x2_26x2_sdk_2_00_00_00")
    parser.add_argument("-b", "--baud",
                        default=12000000,
                        help="baud rate of the serial port, default is 12000000 bps")
    parser.add_argument('-c', '--clock',
                        default=48000000,
                        help=' Clock speed of embedded processor. Default is 48 MHz')
    parser.add_argument('-v', '--verbose',
                        default=30,
                        help=' default is 30 (WARNING), other possible values: 10 (DEBUG), 20 (INFO)')
    parser.add_argument('-id', '--streamId',
                        default="default",
                        help='Set id for wlogger purpose')
    parser.add_argument('-l', '--log',
                        default=".",
                        help='Log Path')
    parser.add_argument('-p', '--pipe',
                        default=None,
                        help='Name of GUI pipe to send data to')
    args = parser.parse_args()

    # Setup Python logging
    if args.pipe is None:
        filename = os.path.join(args.log, 'sl_swo.log')
    else:  # Gandelf needs uniquely named logs for multiple simultaneous logger instances
        filename = os.path.join(args.log, 'sl_swo_' + str(uuid.uuid4()) + '.log')

    logging.basicConfig(level=int(args.verbose),
                        filename=filename,
                        filemode="w",
                        format="%(asctime)s - %(name)s: \n   %(message)s")
    logger = logging.getLogger("main")
    print("\nWriting to log at {}\n".format(os.path.abspath(filename)))
    logger.critical("Logger Started")

    ser = None

    try:
        if args.pipe is not None:
            # Open Wireshark output module
            pipe_open(args.pipe)
            gandelf_send_message(args.streamId, "See python log at {}".format(os.path.abspath(args.log)))
        # Parse the elf file and initialize databases
        db = TraceDB(args.elf, args.sdk_path)
        # Create ITM parser
        itm_q = queue.Queue()
        itm = ITMFramer(itm_q)
        # Create SWO parser
        swo = SWOFramer(db, int(args.clock))
        # Create and start serial receiver
        ser = SerialRx(args.port, baud=int(args.baud))
        if args.pipe is not None:
            gandelf_send_message(args.streamId, "Successfully connected to {} ..... ".format(args.port))
        # Add in module parsers
        module_map = {
            "SWO_LogModule_BLEStack": BLEFramer(),
            #"SWO_LogModule_Driver": DriverFramer(db),
            # "SWO_LogModule_KernelLog" : TIRTOSFramer(db)
        }

        # Main processing loop
        logger.info("Starting main logger loop")
        buf = bytearray()
        while True:
            # Get data from serial and append to buffer
            buf += ser.receive()
            # Sleep for serial read period if not enough data to parse
            if len(buf) <= MAX_ITM_FRAME_SIZE:
                time.sleep(ser.timeout)
            else:
                # Pass buffer to ITM framer. This will parse the entire buffer until it is empty, placing on its queue,
                # returning any unparsed data
                buf = itm.parse(buf)
                # Get all parsed ITM frames
                while True:
                    # Receive, forward, and output all parsed ITM frames
                    try:
                        itm_frame = itm_q.get(block=False)
                        if itm_frame is not None:
                            # Try to build SWO frame from ITM frame
                            swo_frame = swo.parse(itm_frame)
                            if swo_frame is not None and swo_frame.output is True:
                                out_frame = None
                                if swo_frame.opcode == SWOOpcode.RESET:
                                    # Reset each module
                                    for x in module_map.values():
                                        x.reset()
                                # Forward parsed swo_frame to the module if it exists
                                try:
                                    out_frame = module_map[swo_frame.module].parse(swo_frame)
                                # If no module, continue with swo frame
                                except KeyError:
                                    out_frame = swo_frame
                                finally:
                                    # Check again since the SWO frame might have been consumed by a parsing module
                                    if out_frame is not None:
                                        if args.pipe is None:
                                            logging.critical(out_frame)
                                        else:
                                            gandelf_send_data(args.streamId, out_frame.wireshark_out)
                    except queue.Empty:
                        break  # No more parsed ITM frames
    except KeyboardInterrupt:
        logger.error("Keyboard interrupt received.")
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        logger.error("{} @ {} {}: ".format(exc_type, fname, exc_tb.tb_lineno) + str(e))
        gandelf_send_message(args.streamId, "Exception occurred :(  See python log.")
    finally:
        # Close RX thread
        if ser is not None:
            ser.close()
        pipe_close()
        sys.exit("exiting Python...")
