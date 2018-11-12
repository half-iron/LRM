"""
Damit diese funktionen funktionieren muss den BBG mit udev rules und fstab einträge konfiguriert werden
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



if __name__=="__main__":

    parser = argparse.ArgumentParser(prog='PROG', description ='XL2 device tools.')
    parser.add_argument('-list_devices', action='store_true',  help='List XL2 device type.')
    parser.add_argument('-test_serial', action='store_true', help='Versucht XL2 seriel anzusprechen mit einem ECHO befehl.')
    parser.add_argument('-to_mass', action='store_true', help='Put XL2 in Mass mode.')
    parser.add_argument('-to_mass_and_mount', action='store_true', help='Put in Mass mode and mount.')
    parser.add_argument('-umount_and_eject', action='store_true', help='put in Mass mode and mount.')
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
        try:
            logger.info("===Init XL2.")
            xl2 = XL2SLM_serial.from_usb_id(logger=logger)
            xl2.open()
        except Exception as e:
            logger.info("===Close XL2 serial connection.")
            xl2.close()
        else:
            logger.info("===Test serial connection.")
            if xl2.test_conn():
                logger.info("XL2 serial conn working.")
            else:
                logger.warning("XL2 serial conn Error.")
            logger.info("===Close XL2 serial connection.")
            xl2.close()

    elif args.to_mass or args.to_mass_and_mount:
        if not XL2_device_exists(XL2_STORAGE_PATH):
            try:
                logger.info("===Init XL2.")
                xl2 = XL2SLM_serial.from_usb_id(logger=logger)
                xl2.open()
            except Exception as e:
                logger.info("===Close XL2 serial connection.")
                xl2.close()
            else:
                logger.info("===Send to MASS device command.")
                try:
                    xl2.to_mass()
                finally:
                    logger.info("Close XL2 serial connection.")
                    xl2.close()
                if XL2_device_exists(XL2_STORAGE_PATH,30):
                    logger.info("===XL2 storage device at {}.".format(XL2_STORAGE_PATH.as_posix()))

                else:
                    logger.error("===XL2 storage not found at {}.".format(XL2_STORAGE_PATH.as_posix()))
                    raise FileExistsError("===XL2 storage not found at {}.".format(XL2_STORAGE_PATH.as_posix()))
        else:
            logger.info("===XL2 storage device already at {}.".format(XL2_STORAGE_PATH.as_posix()))

        if args.to_mass_and_mount :
            logger.info("===Mount XL2 storage device at {}.".format(MOUNT_PATH.as_posix()))
            mount_XL2_at_storageXL2()
            time.sleep(1)
            if XL2_device_exists(MOUNT_PATH, 5):
                logger.info("===Mount ok.")
            else:
                logger.error("===Mount error.")

    elif args.umount_and_eject:
        if XL2_device_exists(XL2_STORAGE_PATH):
            try:
                umount_XL2_from_storageXL2()
            except Exception as e:
                logger.warning("Umount failed.")
            else:
                logger.info("Umount Ok.")

            logger.info("Eject {}.".format(XL2_STORAGE_PATH.as_posix()))
            eject_XL2storage_dev()
            if XL2_device_exists(XL2_SERIAL_PATH,20):
                logger.info("===Eject ok, found {}.".format(XL2_SERIAL_PATH.as_posix()))
            else:
                logger.error("===Eject error.")
                raise FileExistsError("===XL2 serial not found at {}.".format(XL2_SERIAL_PATH.as_posix()))

        else:
            logger.error("===XL2 storage not found at {}.".format(XL2_STORAGE_PATH.as_posix()))

    elif args.cycle_power:
        #
        relay_cycle_power(logger)
        if XL2_device_exists(XL2_SERIAL_PATH, 30):
            logger.info("===ok, found {}.".format(XL2_SERIAL_PATH.as_posix()))
        else:
            logger.error("===error.")
            raise FileExistsError("===XL2 serial not found at {}.".format(XL2_SERIAL_PATH.as_posix()))

    #
    logger.info("===Exit XL2device.py")