
import datetime
import json
import time

from digi.xbee.devices import TimeoutException, IOMode
from digi.xbee.io import IOLine
import queue

#===========
#MSG PROTOCOL
#============
#ADDRESS 1st Byte
MSG_ADDRESS_TO = 0x0F
MSG_ADDRESS_FROM= 0xF0
ADDRESS_DICT={0:"master",1:"ax_1"}

#HEADERS 2nd Byte

#DATA HEADERS (no RESPONSE)
MSG_HEADER_START=1
MSG_HEADER_STOP =2
MSG_HEADER_AXLE =3
MSG_HEADER_ERROR =18

HEADER={1:'start',2:'stop',3:'axle',18:'error'}

def address_from_to(from_achs,to_master):
    return 0xff&((from_achs<<4)|to_master)

# https://eli.thegreenplace.net/2009/08/12/framing-in-serial-communications/

START = 0x7C  # 124 |
STOP = 0x7D  # 125 }
ESC = 0x7E  # 126 ~

def frame_stuffing(unstuffed):
    stuffed = bytearray()
    stuffed.append(START)
    # escape
    for i in unstuffed:
        if i in [START, STOP, ESC]:
            stuffed.append(ESC)
            stuffed.append(i)
        else:
            stuffed.append(i)
    stuffed.append(STOP)
    return stuffed

def unstuff_frame_from_serial_data():
    unstuffed_frames=[]
    _partial_frame=None
    esc=None
    while True:
        new_bytes = yield unstuffed_frames
        unstuffed_frames=[]
        for b in bytearray(new_bytes):
            if esc:
                esc = False
                if isinstance(_partial_frame, bytearray):
                    _partial_frame.append(b)
            elif b == ESC:
                esc = True
            elif b == START:
                _partial_frame = bytearray()
            elif b == STOP:
                if isinstance(_partial_frame, bytearray):
                    unstuffed_frames.append(_partial_frame)
                _partial_frame = None
            else:
                if isinstance(_partial_frame, bytearray):
                    _partial_frame.append(b)

def parse_msg(frame):
    address_byte=frame[0]
    header=HEADER.get(frame[1],'not_implemented')
    raw_data= frame[2:]
    d={
        'from':ADDRESS_DICT.get((address_byte&MSG_ADDRESS_FROM)>>4,'unknow'),
        'to': ADDRESS_DICT.get(address_byte&MSG_ADDRESS_TO,'unknow'),
        'header':header,
    }
    data={}
    #
    if header=='start':
        data['passby']=int.from_bytes(raw_data[0:2],'little')

    elif header == 'stop':
        data['passby'] = int.from_bytes(raw_data[0:2],'little')
        data['tot_axle'] = int.from_bytes(raw_data[2:4],'little')
        data['stop_time'] = int.from_bytes(raw_data[4:8],'little')/1000
    elif header=='axle':
        data['passby'] = int.from_bytes(raw_data[0:2],'little')
        data['axle'] = int.from_bytes(raw_data[2:4],'little')
        data['axle_time'] = int.from_bytes(raw_data[4:8],'little')/1000
    elif header=='error':
        pass
    else:
        pass
    d.update(data)
    return d



class AxleSensor(object):
    #connected IO
    VBAT_PIN = IOLine.DIO0_AD0
    VBAT_SCALING = 21.2/1.01# reistenze v_misurata = Vbatteria*R1/(R1+R2)
    RESET_PIN = IOLine.DIO3_AD3
    SLEEP_PIN = IOLine.DIO1_AD1
    INIT_PIN = IOLine.DIO2_AD2


    def __init__(self, remote_xbee):
        self._xbee=remote_xbee
        self._local_xbee=self._xbee.get_local_xbee_device()
        #setup io
        #battery
        self._xbee.set_io_configuration(self.VBAT_PIN, IOMode.ADC)
        #hard reset
        self._xbee.set_io_configuration(self.RESET_PIN, IOMode.DIGITAL_OUT_HIGH)
        #sleep
        self._xbee.set_io_configuration(self.SLEEP_PIN, IOMode.DIGITAL_OUT_LOW)
        #setup
        self._xbee.set_io_configuration(self.INIT_PIN, IOMode.DIGITAL_OUT_LOW)
        #self._logger=logger
        self._rx_queque = queue.Queue()

    def ping(self):
        self._local_xbee.set_sync_ops_timeout(0.1)
        try:
            self._local_xbee.send_data(self._xbee, 'ping')
        except TimeoutException:
            s = 'Device {} is not alive'.format(self._xbee.get_node_id())
            #self._logger.error(s)
            #print(s)
            return False
        else:
            return True
        finally:
            self._local_xbee.set_sync_ops_timeout(1)

    def put_rx_msg(self,msg):
        self._rx_queque.put(msg,block=False)

    def get_rx_msg(self,wait=False):
        return self._rx_queque.get(wait)

    def __str__(self):
        a=self.get_64bit_addr()
        return "Axle Sensor {}.".format(a[0:4])

    def __repr__(self):
        return self.__str__()

    def get_64bit_addr(self):
        print("ping success")
        return self._xbee.get_64bit_addr()

    def reset(self):
        self._xbee.set_io_configuration(self.RESET_PIN, IOMode.DIGITAL_OUT_LOW)
        time.sleep(1)
        self._xbee.set_io_configuration(self.RESET_PIN, IOMode.DIGITAL_OUT_HIGH)

    def sleep(self):
        self._xbee.set_io_configuration(self.SLEEP_PIN, IOMode.DIGITAL_OUT_LOW)
        self._xbee.set_io_configuration(self.INIT_PIN, IOMode.DIGITAL_OUT_LOW)

    def wake_up(self):
        self._xbee.set_io_configuration(self.SLEEP_PIN, IOMode.DIGITAL_OUT_HIGH)
        self._xbee.set_io_configuration(self.INIT_PIN, IOMode.DIGITAL_OUT_HIGH)

    def get_vbat(self):
        v = self._xbee.get_adc_value(self.VBAT_PIN)*(1.2/1024)
        return v*self.VBAT_SCALING

def init_axle_sensors_network(xnet,config):
    #expected axle sensors
    expected_devices = [ax['address'] for ax in config.axle_sensors]
    #assigned axle sensors
    axle_sensors = []
    ##
    unexpected_devices=[]
    for device in xnet.get_devices():
        if device.get_64bit_addr() in expected_devices:
            #remove devices
            expected_devices.pop(expected_devices.index(device.get_64bit_addr()))
            axle_sensors.append(AxleSensor(device))
            print('discovered', device)
        elif device.get_64bit_addr() ==config.xbee_coordinator['address']:
            pass
        else:
            unexpected_devices.append(device)
    if len(unexpected_devices):
        print('Unexpected devices: ', unexpected_devices)
    #raise error if missing devices
    if len(expected_devices):
        raise(IOError)
    else:
        return axle_sensors

##dovrà essefre esteso per piu sensori. il file deve rimanere univoco per ogni registrazione. Se ci sono più binari
# e quindi piu passby contempornei possibili ci sara un passby principale(binario) e altri secondari
class TrainPassby(object):
    DICT_KEYS=set(["ax1_time","stop_rec","start_rec","rec_n","ax1_passby", "trigger"])
    def __init__(self,rec_n,stop_delay=15, max_duration=90):
        self.ax_start_time=None
        self.ax_stop_time=None
        #
        self.stop_delay=datetime.timedelta(seconds=stop_delay)
        self.max_duration=datetime.timedelta(seconds=max_duration)
        self.timed_out = False
        #
        self.errors=[]
        self._d = {"rec_n":rec_n,'ax1_time':[]}
        #self.rec_state=False

    @property
    def is_complete(self):
        return set(self._d.keys())==TrainPassby.DICT_KEYS

    @property
    def start_rec(self):
        if self.ax_start_time is not None:
            return True
        else:
            return False

    @property
    def stop_rec(self):
        if self.ax_stop_time is not None:
            if (self.ax_stop_time+self.stop_delay)<=self.now():
                return True

        elif self.ax_start_time is not None:
            if (self.ax_start_time+self.max_duration)<=self.now():
                #timed out
                if not self.timed_out:
                    self.timed_out=True
                    self.add_error("timed_out")
                return True
        else:
            return False

    @property
    def _name(self):
        name= "{rec_n}_{start_rec:%Y_%m_%d_%Hh%Mm}".format(**self._d)
        err = len(self.errors)
        return name +"_"+ str(err)

    def add_axle_data(self,header, timestamp,passby=None,axle=None,axle_time=None,**kwargs):
        #if passby != self._d['ax1_passby']:
        #    raise Exception("passby number changed")

        if header=="error":
            self.errors.append(('ax1_error',timestamp))

        elif header=="stop":
            self.ax_stop_time=timestamp
            self.stop=True

        elif header=="start":
            self.ax_start_time=timestamp
            self._d['ax1_passby']= passby
            self._d['ax1_time'].append((axle,axle_time,timestamp))

            self._d['trigger'] = "ax1"
        elif header =="axle":
            self._d['ax1_time'].append((axle,axle_time,timestamp))

    def add_error(self,err="timeout"):
        self.errors.append((err,self.now()))

    def add_weather_info(self):
        self._d['weather']={}

    def set_rec_stop_time(self):
        if self.stop_rec:
            self._d['stop_rec']= self.now()
        else:
            raise Exception("")

    def set_rec_start_time(self):
        self._d['start_rec']= self.now()

    def set_xl2_BBG_sync_time(self, xl2time):
        self._d['sync_time']= {"xl2":xl2time,"BBG":self.now()}


    def now(self):
        return datetime.datetime.now()

    def export(self,path,force= False):
        filePath = path.joinpath(self._name+".json")
        self._d['errors']=self.errors
        self._d['name'] = self._name
        with filePath.open('w') as f:
            json.dump(self._d, f,indent=2,sort_keys=True,default=str)



if __name__=="__main__":


    if 1:
        import importlib
        import serial
        try:
            config = importlib.import_module('config')
            device = config.serial_port_by_vid_pid(*config.serial_adapter_id)
            s= serial.Serial(device, baudrate=config.axle_sensors[0]['baudrate'])
            print(s.get_settings())
            msg = frame_stuffing(bytearray([address_from_to(1,0),MSG_HEADER_START,1,2,3,4,5,6,7,8]))
            print(msg)
            print(s.write(msg))
            s.flushOutput()
        except Exception as e:
            raise(e)
        finally:
            s.close()

    else:
        import pathlib


        # from other.example_axle_data import ax_example
        PATH0 = pathlib.Path('test')
        passbyPath = PATH0

        g_msg_Q = queue.Queue()
        TIME = []

        for msg in ax_example[0]:
            g_msg_Q.put(msg)
            TIME.append(msg['timestamp'])

        print('t0', min(TIME))
        DT = datetime.datetime.now() - min(TIME)


        def now():
            t = datetime.datetime.now() - DT - datetime.timedelta(0, 1, 0, 0, 0, 0, 0)
            return t


        class TrainPassby2(TrainPassby):
            def now(self):
                return now()


        npassby = 0
        passby = TrainPassby2(npassby)
        REC = False
        Mess = 1
        print("for loop")
        while Mess:

            time.sleep(0.001)
            if passby.start_rec:
                if not REC:
                    REC = True
                    print("start")
                    passby.set_rec_start_time()
                    # if measurement has started
                if passby.stop_rec:
                    if REC:
                        REC = False
                        print("Stop measurement")
                        passby.set_rec_stop_time()
                        passby.export(passbyPath)
                        # reset passby
                        npassby += 1
                        passby = TrainPassby2(npassby)
                        Mess = 0

            if not g_msg_Q.empty():
                msg = g_msg_Q.get()
                timestamp = msg['timestamp']

                while now() <= timestamp:
                    time.sleep(0.002)
                    pass
                print("{}:{}".format(now(), msg))
                passby.add_axle_data(**msg)
