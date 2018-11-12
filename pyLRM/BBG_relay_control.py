import Adafruit_BBIO.GPIO as gpio
import time

POWER_GPIO = "P9_29"  # GPIO_121
PIN = POWER_GPIO
# PIN HIGH -> RELAY close
# PIN LOW -> RELAY open

def relay_setup_gpio():
    gpio.setup(PIN,gpio.OUT,gpio.PUD_DOWN)
    #gpio.setup(POWER_GPIO, gpio.OUT, gpio.HIGH, 100)

def relay_turn_on():
    gpio.output(PIN,0)

def relay_turn_off():
    gpio.output(PIN,1)

def relay_cycle_power(logger):
    logger.info("===Power Cycle xl2.")
    logger.debug("setup gpio")
    relay_setup_gpio()
    logger.info("Power OFF.")
    relay_turn_off()
    time.sleep(1)
    logger.info("Power ON.")
    relay_turn_on()




