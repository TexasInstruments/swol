# Copyright (c) 2018-2019 Texas Instruments Incorporated. All rights reserved.
#
# Log serial port and parse received ITM frames
#####################################################################################

import sys
import os
import logging
import argparse
import time
import queue

from serial_rx import SerialRx
from . import ITMFramer

######################################################
###  MAIN  ##################
if __name__ == '__main__':
    assert sys.version_info >= (3, 7)
    """ This is the Main Function """
    parser = argparse.ArgumentParser(description='Used to log serial port and parse received ITM frames.')
    parser.add_argument("port",
                        help="Com port to open. for win: COM54, for mac: /dev/tty.usbmodemXXX")
    parser.add_argument("-b", "--baud",
                        default=12000000,
                        help="baud rate of the serial port, default is 6000000 bps")
    parser.add_argument('-v', '--verbose',
                        default=20,
                        help=' default is 20 (INFO), other possible values: 10 (DEBUG), 30 (WARNING)')
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
    logger.critical("ITM example Started")

    # Create and start serial receiver
    serial_rx = SerialRx(args.port, int(args.baud))
    # Create and start parser
    itm_frame_q = queue.Queue()
    itm = ITMFramer(itm_frame_q)

    # Loop, receiving data and sending to ITM framer
    buf = bytearray()
    try:
        while True:
            buf += serial_rx.receive()
            if len(buf) == 0:
                time.sleep(0.3)
            else:
                # Pass buffer to ITM framer
                buf = itm.parse(buf)
                # Get all parsed ITM frames
                while True:
                    # Receive all pared ITM frames
                    try:
                        frame = itm_frame_q.get(block=False)
                        logger.info(str(frame))
                    except queue.Empty:
                        break
                    except Exception as e:
                        logger.error(e)
                        break

    except Exception as e:
        logger.critical(e)
    except KeyboardInterrupt:
        logger.error("Keyboard interrupt received.")
    finally:
        # Close RX thread
        serial_rx.close()
        sys.exit("exiting Python...")
