"""The xl2.py module implement the XL2 device.

"""

import os
import time
import subprocess
import pathlib, shutil
import logging
import serial
from serial.tools import list_ports
from datetime import datetime
from .message import ECHO, SYSTEM_MSDMAC, RESET, SYSTEM_KEY, QUERY_SYSTEM_ERROR, QUERY_IDN, \
    SYSTEM_KLOCK, QUERY_SYSTEM_DATE, QUERY_SYSTEM_TIME


class XL2Error(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class XL2SLM_serial(object):
    """The XL2 device object.

    Attributes
    -----------
        serialDev : str
            device path in serial modus
        storageDev : str
            device path in mass storage modus
        mountDir : str
            directory path where device is automatically mounted
    """

    USB_MANUFACTURER_ID = 0x1a2b
    USB_PRODUCT_ID = 0x0004

    def __init__(self, port=None, logger=None, debug=False):
        """Initiate

        Parameters
        ----------
        port : str
            XL2 device file when in serial modus§§

        """
        if logger is None:
            self.logger = logging.getLogger('ntixl2.xl2')
            if debug:
                self.logger.setLevel('DEBUG')
            else:
                self.logger.setLevel('INFO')
        else:
            self.logger =logger.getChild(self.__class__.__name__)

        self.port = port
        self._defaut_timeout = 1.5
        self.conn = serial.Serial(baudrate=9600, timeout=self._defaut_timeout)

    def open(self):
        if not self.conn.is_open:
            try:
                self.conn.setPort(self.port)
                self.conn.open()
            except serial.SerialException as e:
                self.logger.critical("Failed to open XL2 device at {} port.".format(self.port))
                raise XL2Error("Failed to open XL2 device at {} port. \nErrorcode: {}".format(self.port, str(e)))
            else:
                self.logger.info("XL2 device open at {} port.".format(self.port))
                time.sleep(0.5)
                self.flush_serial()
        else:
            self.logger.info("XL2 device already open at {} port.".format(self.port))

    def close(self):
        self.conn.close()
        self.logger.info("XL2 device at {} port closed.".format(self.port))

    def flush_serial(self):
        b = self.conn.read_all()
        if len(b):
            self.logger.warning('There was some unexpected bytes on serial RX buffer: {}.'.format(b.decode('ascii')))

    def set_serial_port_by_id(self, ids=None):
        if ids==None:
            vid, pid = self.USB_MANUFACTURER_ID, self.USB_PRODUCT_ID
        else:
            vid, pid=ids
        self.logger.debug("Search serial device with vid:{} and pid:{}.".format(vid, pid))
        found = False
        for p in list_ports.comports():
            if (p.vid, p.pid) == (vid, pid):
                self.logger.info('Found serial device {} with device name {}.'.format(p.description, p.device))
                if p.device != self.port:
                    self.logger.info('Replace device {} with device name {}.'.format(self.port, p.device))
                    self.port = p.device
                    if self.conn.is_open:
                        self.close()
                        self.open()
                found = True
        if not found:
            self.logger.debug("No serial device with vid:{} and pid:{} found.".format(vid, pid))
            raise XL2Error("No serial device with vid:{} and pid:{} found.".format(vid, pid))

    def serial_message(self, message, wait=1):
        """

        Parameters
        ----------
        message : :obj:`ntixl2.message.Message` object
        wait : float
            Connection timeout to wait for serial line read in case of message without expected answers.

        Returns
        -------
        dict
            parsed message answers according to message object if message has answers. else **None**
            See :meth:`ntixl2.message.Message.parse_answers`

        Note
        ----
        for messages with answers the connection read timeout is set to 5 seconds.

        """
        # write message
        self.flush_serial()
        self.logger.debug("Send message {!r}.".format(str(message)))
        self.conn.write(str(message).encode('ascii'))
        # read returmn lines
        if message.RETURN is not None:
            self.logger.debug("Message is query")
            self.conn.timeout = wait
            ret = []
            for i in range(message.return_lines()):
                line = self.conn.readline()
                if len(line):
                    ret.append(line.decode('ascii'))
                    self.logger.debug("Returned line: {!r}".format(line.decode('ascii')))
                else:
                    self.conn.timeout = self._defaut_timeout
                    self.logger.error(
                        'After sending {} message expected some lines on RX serial. Recieved 0 bytes'.str(message))
                    raise XL2Error('Expected some lines on RX serial. Recieved 0 bytes')
            # reset timeout
            self.conn.timeout = self._defaut_timeout
            return message.parse_answers(ret)
        else:
            return None

    def test_conn(self):
        # test if connection si active
        mess = ECHO('ping')
        try:
            ret = self.serial_message(mess)
        except (serial.SerialException, AttributeError) as e:
            # raise (e)
            self.logger.error("Ping: error.")
            return False
        else:
            self.logger.debug('Ping: ok.')
            return ret['string'] == mess.param_str

    def reset(self):
        """ Reset the XL2 device

        See Also
        --------
        :class:`ntixl2.message.RESET`

        """
        self.logger.info("Reset device.")
        self.serial_message(RESET())
        time.sleep(3)

    def check_errors(self):
        """ Read the XL2 Error queue and return a list of errors

        Returns
        -------
        list
            list of errors

        See Also
        --------
        :class:`ntixl2.message.QUERY_SYSTEM_ERROR`

        """
        return self.serial_message(QUERY_SYSTEM_ERROR())

    def identification(self):
        """ Return the XL2 device identification data

        Returns
        -------
        dict
            identification dict

        See Also
        --------
        :class:`ntixl2.message.QUERY_IDN`

        """
        return self.serial_message(QUERY_IDN())

    def get_datetime(self):
        date = self.serial_message(QUERY_SYSTEM_DATE(),1.5)
        time = self.serial_message(QUERY_SYSTEM_TIME(),1.5)
        date['year']+=2000
        return datetime(**{**date, **time})


    def klock(self, locked=False):
        """Lock unlock XL2 keyboard

        Parameters
        ----------
        locked : bool
            if True lock keyboard else unlock

        """
        if locked:
            self.serial_message(SYSTEM_KLOCK.ON())
        else:
            self.serial_message(SYSTEM_KLOCK.OFF())

    def to_mass(self):
        """ Switch the device into MASS status.

        send a serial message to switch the XL2 device to "MASS" status.


        Note
        ----
            The function is blocking till the switch is successful. This can take many seconds.

        See Also
        --------
        :func:`ntixl2.xl2.safe_remove_mass_storage_device`

        """
        # TODO:
        #    stop measurement
        self.reset()
        self.logger.info("Send Mass Storage command.")
        mess = SYSTEM_MSDMAC()
        try:
            self.serial_message(mess)
        except serial.SerialException:
            self.logger.info("Serial connection is down.")
        finally:
            self.close()
        self.logger.info("Sleep 15s.")
        time.sleep(15)

    def select_profile(self, profile=5):
        """ Reset device and load the wanted profile

        The profile number refer to the profile order in the profile Menu

        Parameters
        ----------
        profile : int
            profile number. The profile number refer to the profile order in the profile menu.

        Note
        ----
        The function wait for the 'OK' status of the :obj:`ntixl2.message.SYSTEM_KEY` message. Another 5 seconds waiting to load the\
        profile

        """
        # reset
        self.reset()
        self.logger.debug("Select measuremet profile {}.".format(profile))
        # key msg
        m = SYSTEM_KEY()
        # select profile
        for par in ['ESC', 'ENTER'] + ['NEXT'] * 8 + ['ENTER'] + ['PREV']+['ENTER'] + ['NEXT'] * profile + ['ENTER']:
            m.param_keys.append_param(par)
        r = self.serial_message(m)
        assert r['status'] == 'ok'
        time.sleep(5)

    @classmethod
    def from_usb_id(cls,ids=None, logger=None, debug=False):
        ist = cls(logger=logger, debug=debug)
        ist.set_serial_port_by_id(ids)
        return ist
