from  digi.xbee.devices import XBee64BitAddress
import time
import platform

SIMULATE=False

mail_handler = {"mailhost":('smtp.gmail.com', 465),
                       "fromaddr":"rblraspberry@gmail.com",
                       "toaddrs":"enzo.scossa.romano@gmail.com",
                       "subject":"Lausanne Triage Messung",
                       "credentials":("rblraspberry@gmail.com","akustik16")
                       }

XL2={'port':None,
     'serial_usb_id':(0x1a2b, 0x0004),
     'mass_usb_id':(0x1a2b, 0x0003),
     'mountDir':"/media/XL2-sd",
     'project_folder_name': "KG",
}

xbee_coordinator= { 'port':"/dev/ttyO4",
                    'node_id':'BBG',
                    'baud_rate':57600,
                    'flow_control':None,#FlowControl.HARDWARE_RTS_CTS,
                    #'address': XBee64BitAddress.from_hex_string("0013A2004166E49B"),
                    'address': XBee64BitAddress.from_hex_string("0013A200414F9054"),
                    'serial_adapter_id':(0x403, 0x6015),# vid, pid adapter FTDI
                   }

axle_sensors=[
        {'address':XBee64BitAddress.from_hex_string("0013A200414F906D"),
         'baudrate': 57600,
         }]

gleise=[{'number':1,
         'AchsSensor':{'A':'Einfahrt'},
         }
        ]


#############
BBG=None
#GPIO with connecter switch to power XL2
POWER_GPIO = "P8_7"
XL2_USB_PORT = 1
HUAWEI_USB_PORT=3


# use of UART4 for DIGI_XBEE serial communication
UART4 = "/dev/ttyO4"
UART4_RX = "P9_11"
UART4_TX = "P9_13"

#########################33
## auto
def serial_port_by_vid_pid(vid,pid):
    from serial.tools import list_ports
    print("Serach serial device with vid:{} and pid:{}.".format(vid,pid))
    for p in list_ports.comports():
        if (p.vid,p.pid) ==(vid,pid):
            print('Found serial device {} with device name {}.'.format(p.description,p.device))
            return p.device
    print("No serial device found.")
    raise FileNotFoundError('serial port device file not found.')

machine=platform.machine()
system= platform.system()

if platform.system()=="Linux":
    if machine == 'armv7l':
        BBG=True
    else:
        BBG = False
        xbee_coordinator['port'] = serial_port_by_vid_pid(*xbee_coordinator["serial_adapter_id"])
else:
    raise SystemError("Measurement systems only works on Linux systems")


if BBG:
    import Adafruit_BBIO.GPIO as gpio
    def setup_gpio():
        gpio.setup(POWER_GPIO, gpio.OUT, gpio.HIGH, 100)

    def turn_XL2_power(power="ON"):
        if power=="ON":
            gpio.output(POWER_GPIO,0)
        elif power=="OFF":
            gpio.output(POWER_GPIO, 1)
        else:
            raise ValueError("power parameter has to be ON or OFF.")
        return 1

    def turn_USB_power(usb_port,power="ON"):
        pass




if SIMULATE:
    axle_sensors =[{'address': XBee64BitAddress.from_hex_string("0013A2004166E49B"),
                    'baudrate': 57600, }]

