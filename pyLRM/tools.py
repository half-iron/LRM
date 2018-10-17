from serial.tools import list_ports
from pyLRM.config import *

def serial_port_by_vid_pid(vid,pid,logger):
    """
    search and return serial port name given vendor and product id
    :param vid: vendor id
    :param pid: product id
    :param logger:
    :return: portname
    """
    logger.debug("Search serial device with vid:{} and pid:{}.".format(vid,pid))
    for p in list_ports.comports():
        if (p.vid,p.pid) ==(vid,pid):
            logger.debug('Found serial device {} with device name {}.'.format(p.description,p.device))
            return p.device
    logger.debug("No serial device found.")
    raise FileNotFoundError('serial port device file not found.')

if BBG:
    import Adafruit_BBIO.GPIO as gpio
    def setup_gpio(logger):
        logger.debug("setup BBG GPIO.")
        gpio.setup(POWER_GPIO, gpio.OUT, gpio.HIGH, 100)

    def turn_XL2_power(power,logger):
        logger.debug("turn_XL2_power:{}.".format(power))
        if power=="ON":
            gpio.output(POWER_GPIO,0)
        elif power=="OFF":
            gpio.output(POWER_GPIO, 1)
        else:
            raise ValueError("power parameter has to be ON or OFF.")
        return 1

    def turn_USB_power(usb_port,power="ON"):
        pass