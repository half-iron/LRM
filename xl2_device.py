"""
Damit diese funktionen funktionieren muss den BBG mit udev rules und fstab einträge konfiguriert werden

Wichtig sind auch folgende settings an XL2:
 - auto serial
 - Auto startup: auto start functionality is enabled by copying a txt-file with the file name “AutoOn.txt” onto the SD Card

"""
from pyLRM.logging_handler import init_logger
import argparse
import os.path
from ntixl2 import XL2SLM_serial
from pyLRM.BBG_relay_control import relay_cycle_power
import pathlib
import subprocess
import time
import os


MOUNT_PATH= pathlib.Path("/home/debian/storageXL2")
XL2_SERIAL_PATH= pathlib.Path("/dev/XL2serial")
XL2_STORAGE_PATH= pathlib.Path("/dev/XL2storage")

def XL2_device_exists(device,timeout=0):
    i=0
    while i<=timeout:
        if os.path.exists(device.as_posix()):
            return True
        time.sleep(1)
        i+=1
    else:
        return False

def mount_XL2_at_storageXL2():
    subprocess.run(["mount", MOUNT_PATH.as_posix()]).check_returncode()

def umount_XL2_from_storageXL2():
    subprocess.run(["umount", MOUNT_PATH.as_posix()]).check_returncode()

def eject_XL2storage_dev():
    subprocess.run(["eject", XL2_STORAGE_PATH.as_posix()]).check_returncode()
    if XL2_device_exists(XL2_SERIAL_PATH, 30):
        logger.info("XL2 serial device at {}.".format(XL2_SERIAL_PATH.as_posix()))
    else:
        raise FileExistsError("XL2 storage not found at {}.".format(XL2_SERIAL_PATH.as_posix()))

def mount_XL2storage():
    if XL2_device_exists(XL2_STORAGE_PATH):
        mount_XL2_at_storageXL2()
    else:
        raise FileExistsError("===XL2 storage not found at {}.".format(XL2_STORAGE_PATH.as_posix()))

def XL2_serial_to_mass(logger):
    logger.info("===Init XL2.")
    xl2 = XL2SLM_serial.from_usb_id(logger=logger)
    try:
        xl2.open()
        logger.info(" Xl2 send to MASS device command.")
        xl2.to_mass()
        if XL2_device_exists(XL2_STORAGE_PATH, 30):
            logger.info("XL2 storage device at {}.".format(XL2_STORAGE_PATH.as_posix()))

        else:
            raise FileExistsError("XL2 storage not found at {}.".format(XL2_STORAGE_PATH.as_posix()))
    finally:
        logger.info("===Close XL2 serial connection.")
        xl2.close()

def XL2_serial_test_conn(logger):
    logger.info("===Init XL2.")
    xl2 = XL2SLM_serial.from_usb_id(logger=logger)
    try:

        xl2.open()

        if xl2.test_conn():
            logger.info("XL2 serial conn working.")
        else:
            logger.error("XL2 serial conn Error.")
    finally:
        logger.info("===Close XL2 serial connection.")
        xl2.close()

if __name__=="__main__":

    parser = argparse.ArgumentParser(prog='PROG', description ='XL2 device tools.')
    parser.add_argument('-list_devices', action='store_true',  help='List XL2 device type.')
    parser.add_argument('-test_serial', action='store_true', help='Versucht XL2 seriel anzusprechen mit einem ECHO befehl.')
    parser.add_argument('-to_mass', action='store_true', help='Put XL2 in Mass mode.')
    #parser.add_argument('-to_mass_and_mount', action='store_true', help='Put in Mass mode and mount.')
    parser.add_argument('-mount', action='store_true', help='Put in Mass mode and mount.')
    parser.add_argument('-umount', action='store_true', help='Umount device.')
    parser.add_argument('-eject', action='store_true', help='eject device. Wait till device in serial mode.')
    parser.add_argument('-cycle_power', action='store_true', help='Turn power to XL2 off and on.')


    args = parser.parse_args()

    logger = init_logger("XL2",
                         filepath=pathlib.Path(),
                         mail=False)
    if args.list_devices:
        if XL2_device_exists(XL2_SERIAL_PATH,0):
            logger.info("==Found serial device {}.".format(XL2_SERIAL_PATH.as_posix()))
        elif XL2_device_exists(XL2_STORAGE_PATH,0):
            logger.info("==Found storage device {}.".format(XL2_STORAGE_PATH.as_posix()))
        else:
            logger.warning("No device found.")

    elif args.test_serial:
        logger.info("===Test serial connection.")
        XL2_serial_test_conn(logger)

    elif args.to_mass:
        logger.info("===XL2_serial to mass.")
        if not XL2_device_exists(XL2_STORAGE_PATH):
            XL2_serial_to_mass(logger)
        else:
            logger.warning("===XL2 storage already at {}.".format(XL2_STORAGE_PATH.as_posix()))
        if args.mount:
            logger.info("===Mount XL2 storage device at {}.".format(MOUNT_PATH.as_posix()))
            mount_XL2storage()

    elif args.mount:
        logger.info("===Mount XL2 storage device at {}.".format(MOUNT_PATH.as_posix()))
        mount_XL2storage()


    elif args.umount:
        logger.info("=== umuount.")
        umount_XL2_from_storageXL2()
        if args.eject:
            logger.info("=== eject.")
            eject_XL2storage_dev()

    elif args.eject:
        logger.info("=== eject.")
        eject_XL2storage_dev()

    elif args.cycle_power:
        #
        relay_cycle_power(logger)
        if XL2_device_exists(XL2_SERIAL_PATH, 30):
            logger.info("===ok, found {}.".format(XL2_SERIAL_PATH.as_posix()))
        else:
            logger.error("===error.")
            raise FileExistsError("===XL2 serial not found at {}.".format(XL2_SERIAL_PATH.as_posix()))
