import Adafruit_BBIO.GPIO as gpio
import time

PIN = "P8_7"
# PIN HIGH -> RELAY close
# PIN LOW -> RELAY open

def relay_setup_gpio():
    gpio.setup(PIN,gpio.OUT,gpio.PUD_DOWN)

def relay_turn_on():
    gpio.output(PIN,0)

def relay_turn_off():
    gpio.output(PIN,1)

if __name__=="__main__":
    WAIT=5
    relay_setup_gpio()
    relay_turn_off(22)
    print("Turn relay off.")
    relay_turn_off()
    time.sleep(1)
    print("Turn relay on and wait {} seconds.".format(WAIT))
    relay_turn_on()
    time.sleep(WAIT)

