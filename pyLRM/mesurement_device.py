from ntixl2 import XL2SLM_serial,XL2SLM_mass_storage
from ntixl2.message import INITIATE

def xl2_init(logger):
    logger.info("Initialte XL2.")
    xl2 = XL2SLM_serial.from_usb_id(logger=logger)
    xl2.open()
    logger.info("open XL2 ok.")
    xl2.reset()
    return xl2


def xl2_setup_measurement(xl2, logger, profile=1):
    #logger.info("Initialte XL2.")
    #xl2 = XL2SLM_serial.from_usb_id(logger=logger)
    #xl2.open()
    logger.info("XL2 select profile")
    xl2.select_profile(profile=profile)
    logger.info("XL2 lock keyboard")
    xl2.klock(locked=True)

def xl2_init_to_mass(logger,massdevice):
    logger.info("Initialte XL2.")
    xl2 = XL2SLM_serial.from_usb_id(logger=logger)
    xl2.open()
    logger.info("open XL2 ok.")
    xl2.to_mass()

    while 15:
        XL2SLM_mass_storage()



if __name__=="__main__":
    import logging,sys
    logger = logging.getLogger()
    h=logging.StreamHandler(sys.stdout)
    logger.addHandler(h)
