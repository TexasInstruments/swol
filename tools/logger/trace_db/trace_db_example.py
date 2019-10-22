# Copyright (c) 2018-2019 Texas Instruments Incorporated. All rights reserved.
#
# Test trace_db module
#####################################################################################

import sys
import os
import logging
import argparse
from trace_db import TraceDB

######################################################
###  MAIN  ##################
if __name__ == '__main__':
    assert sys.version_info >= (3, 7)
    """ This is the Main Function """
    parser = argparse.ArgumentParser(
        description='Used to receive from serial port and print to console. Send ctrl+c twice to stop.')
    parser.add_argument("elf",
                        help="Elf file where the trace strings need to be extracted from")
    parser.add_argument("-s", "--sdk_path",
                        default="",
                        help="Path to the SDK. Used to pick up ROM symbols. Example: C:\ti\simplelink_cc13x2_26x2_sdk_2_00_00_00")
    parser.add_argument('-v', '--verbose',
                        default=10,
                        help=' default is 10 (DEBUG), other possible values: 20 (INFO), 30 (WARNING)')
    parser.add_argument('-l', '--log',
                        default="logger.log",
                        help='Log file')
    args = parser.parse_args()

    # Setup Python logging
    logging.basicConfig(level=int(args.verbose),
                        filename=args.log,
                        filemode="w",
                        format="%(asctime)s - %(name)s: \n   %(message)s")
    logger = logging.getLogger("main")
    print("\nWriting to log at {}\n".format(os.path.abspath(args.log)))
    logger.critical("TraceDB example Started")

    try:
        db = TraceDB(args.elf, args.sdk_path)
    except Exception as e:
        logger.error(e)
    except KeyboardInterrupt:
        logger.critical("Keyboard interrupt received.")
    finally:
        sys.exit("exiting Python...")
