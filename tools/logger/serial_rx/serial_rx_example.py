# Copyright (c) 2018-2019 Texas Instruments Incorporated. All rights reserved.
#
# Log serial port
#####################################################################################

import sys
import os
import logging
import argparse
from . import SerialRx
import time

######################################################
###  MAIN  ##################
if __name__ == '__main__':
    assert sys.version_info >= (3, 7)
    """ This is the Main Function """
    parser = argparse.ArgumentParser(
        description='Used to receive from serial port and print to console. Send ctrl+c twice to stop.')
    parser.add_argument("port",
                        help="Com port to open. for win: COM54, for mac: /dev/tty.usbmodemXXX")
    parser.add_argument("-b", "--baud",
                        default=12000000,
                        help="baud rate of the serial port, default is 12000000 bps")
    parser.add_argument('-v', '--verbose',
                        default=20,
                        help=' default is 20 (INFO), other possible values: 10 (DEBUG), 30 (WARNING)')
    parser.add_argument('-t', '--timeout',
                        default=1,
                        help='serial read timeout in seconds, default is 2')
    parser.add_argument('-c', '--chunk',
                        default=100,
                        help='Max amount of data read per serial read, default is 100')
    parser.add_argument('-p', '--parity',
                        default='N',
                        help='Parity: default is N (None). Other options are E (even), O (odd), M (mark) and S (space)')
    parser.add_argument('-s', '--stopbits',
                        default=1,
                        help='Number of stopbits: default is 1. Other options are 1.5 and 2')
    parser.add_argument('-y', '--bytesize',
                        default=8,
                        help='Byte size in bits: default is 8. Other options are 5, 6, and 7')
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
    logger.critical("Serial RX example Started")

    # Create and start serial receiver
    serial_rx = SerialRx(args.port, int(args.baud), int(args.timeout), int(args.chunk),
                         args.parity, int(args.stopbits), int(args.bytesize))

    # Continuously receive and display until keyboard interrupt
    try:
        while True:
            buf = serial_rx.receive()
            if len(buf) == 0:
                logger.debug("No data received")
                time.sleep(0.3)
            else:
                logger.info("%d bytes received\n " % len(buf) + " ".join("{0:#0{1}x}".format(x, 4) for x in buf))
    except Exception as e:
        logger.error(e)
    except KeyboardInterrupt:
        logger.critical("Keyboard interrupt received.")
    finally:
        # Close RX thread / process
        serial_rx.close()
        sys.exit("exiting Python...")
