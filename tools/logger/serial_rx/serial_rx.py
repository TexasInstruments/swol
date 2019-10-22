"""Class to receive from serial port"""

import threading
import time
import queue
import serial
import logging

logger = logging.getLogger("Serial Rx")

verbose_rx = 0  # Set to 1 to show received serial data


def receive_thread(ser, chunk_size, q, stop_event):
    """Target thread for SerialRx
    
    Can be stopped with SerialRx.close

    Args:
      ser: serial instance
      chunk_size: maximum byte size to read for
      q: output queue, can be read with :method:receive
      stop_event: used by close() to end this thread

    Returns:

    """
    while not stop_event.is_set():
        # Read chunk bytes at a time or until read times out
        buf = ser.read(size=chunk_size)
        # If there was data
        if len(buf) > 0:
            # Enqueue read buffer
            if verbose_rx:
                logger.debug("SERIAL Stream of size %d:" % len(buf) + "".join(["0x%x " % i for i in buf]))
            # Put on output queue
            try:
                q.put(buf)
            except Exception as e:
                logger.error(e)
        time.sleep(0.001)


class SerialRx(object):
    """Create a thread to receive from serial port.
    
    Reads for timeout or chunk_size, whichever happens first, then places received data on queue which can be read
    with receive

    Args:
        port: port to receive on, for win: COM54, for mac: /dev/tty.usbmodemXXX
        baud: baud rate
        timeout: maximum time to read before placing data on output queue
        chunk_size: maximum bytes to read before placing data on output queue
        parity: parity (from serial module)
        stopbits: stopbits (from serial module)
        bytesize: bytesize (from serial module)
    """

    def __init__(self, port, baud=12000000, timeout=0.2, chunk_size=1000, parity=serial.PARITY_NONE,
                 stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS):
        self.timeout = timeout
        # Check port path for corner case
        if (port[0] != '\\') and ('/dev' not in port):
            port = '\\\\.\\' + port
        # Open serial port
        self._ser = serial.Serial(port=port, baudrate=baud, timeout=timeout, parity=parity, stopbits=stopbits,
                                  bytesize=bytesize)
        if not self._ser.isOpen():
            raise Exception('COM port error')
        # On MAC, at least one byte needs to be read in order for in_waiting to be reliable.
        self._ser.read(1)
        logger.critical("Serial port opened")
        # Create and start receive thread
        self._stop_event = threading.Event()
        self._rxq = queue.Queue()
        self._rx_thread = threading.Thread(target=receive_thread,
                                           args=(self._ser, chunk_size, self._rxq, self._stop_event))
        self._rx_thread.daemon = True
        self._rx_thread.start()

    def receive(self):
        """Try to read received data from internal queue

        Returns:
            bytes of data or empty bytes
        """
        try:
            result = self._rxq.get(block=False)
        except queue.Empty:
            return bytes()
        else:
            return result

    def close(self):
        """Stop the receive thread and close the serial port"""
        # Stop thread
        logger.critical("Stopping serial thread")
        self._stop_event.set()
        self._rx_thread.join()
        # Close serial port
        logger.critical("Closing serial port")
        self._ser.close()
