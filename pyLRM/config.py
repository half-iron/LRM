from  digi.xbee.devices import XBee64BitAddress

XL2={'port':None,
     'serial_usb_id':(0x1a2b, 0x0004),
     'mass_usb_id':(0x1a2b, 0x0003),
     'mountDir':"/media/XL2-sd",
     'project_folder_name': "KG",
     }

xbee_BBG= {'port':"/dev/ttyO4",
           'baud_rate':115200,
           'address': XBee64BitAddress.from_hex_string("0013A2004166E49B")
           }

xbee_test={'serial_adapter_id': (0x403, 0x6015), # vid, pid of UART2USB adapter, FTDI chip
            'baud_rate':115200,
            'address': XBee64BitAddress.from_hex_string("0013A200414F9054")
           }

xbee_axle_sensors={'Einfahrt':XBee64BitAddress.from_hex_string("0013A20041863136"),
                   'Ausfahrt':XBee64BitAddress.from_hex_string("0013A200414F906D")
                   }


#############
#BBG settings
BBG=False
if BBG:
    #GPIO with connecter switch to power XL2
    POWER_GPIO = "P8_7"
    # use of UART4 for DIGI_XBEE serial communication
    UART4_RX_GPIO = "P9_11"
    UART4_TX_GPIO = "P9_13"
    #XL2_USB_PORT = 1
    #HUAWEI_USB_PORT=3


###############
#account settings for logger mail handler
mail_handler = {"mailhost":('smtp.gmail.com', 465),
                       "fromaddr":"rblraspberry@gmail.com",
                       "toaddrs":"enzo.scossa.romano@gmail.com",
                       "subject":"Lausanne Triage Messung",
                       "credentials":("rblraspberry@gmail.com","akustik16")
                       }








