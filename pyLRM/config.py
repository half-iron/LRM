from  digi.xbee.devices import XBee64BitAddress
import datetime
import yaml
import pathlib
from pyLRM.passby import TrainPassby

secret = yaml.load(pathlib.Path().absolute().joinpath('accounts.secret.yaml').open("r+"))

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

#account settings for logger mail handler
mail_handler = {"mailhost":('smtp.gmail.com', 465),
                       "fromaddr":secret['LRM_mail_account']['mail'],
                       "toaddrs":"enzo.scossa.romano@gmail.com",
                       "subject":"Luzern Messung",
                       "credentials":("rblraspberry@gmail.com",secret['LRM_mail_account']['pw'])
                       }

##subclass trainpassby
## TODO:    pyLRM.passby.TrainPassby class muss überdacht werden damit subclassing übersichtlich wird.
#           Die methode rec entählt die Logik zum triggern
#           Die Idee ist dass die methode rec messspezifisch ist und deswegen hier im config implementiert wird

class MyTrainPassby(TrainPassby):
    def rec(self):
        ax1_count, ax2_count=[self._ax_counter[n] for n in self.ax_names]
        if self._stopped or self.is_error:
            return False
        elif self._start_time is None:
            if ax1_count==self._start_after_ax:
                if ax2_count==0:
                    self._start_time=self._now()
                    self._ax_trigger=self.ax_names[0]
                    return True
                else:
                    self.add_error('error1')
                    return False
            elif ax2_count==self._start_after_ax:
                if ax1_count==0:
                    self._start_time=self._now()
                    self._ax_trigger=self.ax_names[1]
                    return True
                else:
                    self.add_error('error2')
                    return False
            else:
                return False
        elif (self._last_ax_timestamp+ self.stop_delay<=self._now()):
            for n in self.ax_names:
                if self._ax_counter[n]<self._ax_counter_low_err:
                    self.add_error('{}_number_low_error'.format(n))
            self._stopped=True
            return False
        else:
            return True

############################
############################
############################
_xbee_axle_sensors_inv = { str(addr):name for name,addr in xbee_axle_sensors.items()}
xbee_axle_sensors_names ={name for name in xbee_axle_sensors.keys()}

def xbee_axle_sensors_name_from_addr(xbeeaddr):
    return _xbee_axle_sensors_inv.get(str(xbeeaddr),None)



