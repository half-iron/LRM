from  digi.xbee.devices import XBee64BitAddress
import datetime

XL2={'port':None,
     'serial_usb_id':(0x1a2b, 0x0004),
     }

xbee_BBG= {'port':"/dev/ttyO4",
           'baud_rate':115200,
           'address': XBee64BitAddress.from_hex_string("0013A2004166E49B")
           }

xbee_test={'serial_adapter_id': (0x403, 0x6015), # vid, pid of UART2USB adapter, FTDI chip
            'baud_rate':115200,
            'address': XBee64BitAddress.from_hex_string("0013A200414F9054")
           }

xbee_axle_sensors={'km94_4':XBee64BitAddress.from_hex_string("0013A20041863136"),#SSA
                   'km94_2':XBee64BitAddress.from_hex_string("0013A200414F906D")#lontano
                   }

AX_SETTINGS_DEFAULTS = [32, 13, 3, 1]
STOP_DELAY = 10
PROFILE = 6
STOP = datetime.datetime.strptime("30/11/18 01:30", "%d/%m/%y %H:%M")

_xbee_axle_sensors_inv = { str(addr):name for name,addr in xbee_axle_sensors.items()}
xbee_axle_sensors_names ={name for name in xbee_axle_sensors.keys()}

def xbee_axle_sensors_name_from_addr(xbeeaddr):
    return _xbee_axle_sensors_inv.get(str(xbeeaddr),None)



###############
#account settings for logger mail handler
mail_handler = {"mailhost":('smtp.gmail.com', 465),
                       "fromaddr":"rblraspberry@gmail.com",
                       "toaddrs":"enzo.scossa.romano@gmail.com",
                       "subject":"Luzern Messung",
                       "credentials":("rblraspberry@gmail.com","LRMessanlage")
                       }








