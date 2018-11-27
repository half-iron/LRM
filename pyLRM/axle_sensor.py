import time
from digi.xbee.devices import TimeoutException, IOMode
from digi.xbee.io import IOLine,IOValue
import struct
import math
# ==========================================================================================
# MSG PROTOCOL
# ============
#
# Messages longer than one byte (MSG from axle_sensor) are always
# stuffed using start ,stop and esc bytes
FRAME_START= (0x7C)
FRAME_STOP =(0x7D)
FRAME_ESC =(0x7E)
#
# MSG from axle_sensor
# ====================
#
# msg_out_axle:
# -------------
# send only in RDY state (green led on)
MSG_HEADER_AXLE=(1)
MSG_HEADER_AXLE_ERROR=(2)
# axle msg frame 6 byte length:
# MSG_HEADER_AXLE:uint_8t,      wheel_On_counter:uint_8t,  wheel_Off_counter:uint_32t
#
# axle error msg frame 4 byte length:
# MSG_HEADER_AXLE_ERROR:uint_8t,wheel_On_counter:uint_8t,   wheel_Off_counter:uint_32t
#
# msg_out_setup: setup response MSG
# ---------------------------------
# send after a msg_in
# always 2 bytes long send only in IDLE state (green_led blinking)
#
#                                 first byte                          second byte
MSG_HEADER_SETUP_OK=(3)     #  MSG_HEADER_SETUP_OK:uint_8t,     msg_in:uint_8t
MSG_HEADER_SETUP_ERROR=(4)  #  MSG_HEADER_SETUP_ERROR:uint_8t,  msg_in in:uint_8t
MSG_HEADER_T_ON=(5)         #  MSG_HEADER_T_ON:uint_8t,         threshold_ON :uint_8t
MSG_HEADER_T_OFF=(6)        #  MSG_HEADER_T_EFF:uint_8t,        threshold_OFF:uint_8t
MSG_HEADER_T_ERR=(7)        #  MSG_HEADER_T_ERR:uint_8t,        threshold_ERR:uint_8t
MSG_HEADER_SUM_LEN=(8)      #  MSG_HEADER_SUM_LEN:uint_8t,      sum_len:uint_8t
MSG_HEADER_ECHO=(0xf1)      #  MSG_HEADER_PING:uint_8t,         msg_in:uint_8t
#
# MSG to axle_sensor
# =================
# msg_in:
# -------
# Always only 1 byte long. Handle only in IDLE state (green_led blinking)
#
# Follow always response msg_out_setup
MSG_GET_SUM_LEN=(1) # response MSG_HEADER_T_ON
MSG_GET_T_ON=(2)    # response MSG_HEADER_T_ON
MSG_GET_T_OFF=(3)   # response MSG_HEADER_T_OF
MSG_GET_T_ERR=(4)   # response MSG_HEADER_T_ERR
#
# Follow always a response MSG_HEADER_SETUP_OK or MSG_HEADER_SETUP_ERROR
MSG_ECHO=(0xf0)  #
MSG_SET_SUM_LEN=(10) #  11-20
MSG_SET_T_ON=(20)   #   20-40
MSG_SET_T_OFF=(40)  #   40-61
MSG_SET_T_ERR=(60)  #   >61


class AxleSensorException(Exception):
    pass


def frame_stuffing(unstuffed):
    # https:# eli.thegreenplace.net/2009/08/12/framing-in-serial-communications/
    stuffed = bytearray()
    stuffed.append(FRAME_START)
    # escape
    for i in unstuffed:
        if i in [FRAME_START, FRAME_STOP, FRAME_ESC]:
            stuffed.append(FRAME_ESC)
            stuffed.append(i)
        else:
            stuffed.append(i)
    stuffed.append(FRAME_STOP)
    return stuffed

def unstuff_frame_from_serial_data():
    # https:# eli.thegreenplace.net/2009/08/12/framing-in-serial-communications/
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
            elif b == FRAME_ESC:
                esc = True
            elif b == FRAME_START:
                _partial_frame = bytearray()
            elif b == FRAME_STOP:
                if isinstance(_partial_frame, bytearray):
                    unstuffed_frames.append(_partial_frame)
                _partial_frame = None
            else:
                if isinstance(_partial_frame, bytearray):
                    _partial_frame.append(b)

# AXLE_SENSOR_COUNTER_SAMPLE_RATE ist von der MSP432 clock abhängig. Die ISR lauft auf 1/16 of ACLK (32MHz).
# der counter incrementiert jede 4 ISR cycles
AXLE_SENSOR_COUNTER_SAMPLE_RATE= 2000./ 4
def parse_msg(frame):
    header=frame[0]
    raw_data= frame[1:]
    d={}
    #
    if header==MSG_HEADER_AXLE:
        on,off =struct.unpack('<BI',raw_data) #little endian unsigned Byte unsigned Int
        d['header'] = "MSG_HEADER_AXLE"
        d['time_wheel_on'] = on / AXLE_SENSOR_COUNTER_SAMPLE_RATE
        d['time_wheel_off'] = off / AXLE_SENSOR_COUNTER_SAMPLE_RATE
    elif header==MSG_HEADER_AXLE_ERROR:
        d['header'] = "MSG_HEADER_AXLE_ERROR"
        d['time_wheel_on'] = None
        d['time_wheel_off'] = int.from_bytes(raw_data[0:4],'little') / AXLE_SENSOR_COUNTER_SAMPLE_RATE
    elif header == MSG_HEADER_SETUP_OK:
        d['header'] = "MSG_HEADER_SETUP_OK"
        d['msg_in'] = raw_data[0]
    elif header == MSG_HEADER_SETUP_ERROR:
        d['header'] = "MSG_HEADER_SETUP_ERR"
        d['msg_in'] = raw_data[0]
    elif header == MSG_HEADER_SUM_LEN:
        d['header'] = "MSG_HEADER_SUM_LEN"
        d['sum_len'] = raw_data[0]
    elif header == MSG_HEADER_T_ERR:
        d['header'] = "MSG_HEADER_T_ERR"
        d['thresholdERR'] = raw_data[0]
    elif header == MSG_HEADER_T_OFF:
        d['header'] = "MSG_HEADER_T_OFF"
        d['thresholdOFF'] = raw_data[0]
    elif header == MSG_HEADER_T_ON:
        d['header'] = "MSG_HEADER_T_ON"
        d['thresholdON'] = raw_data[0]
    elif header == MSG_HEADER_ECHO:
        d['header'] = "MSG_HEADER_PING"
        d['echo'] = raw_data[0]-MSG_ECHO
    else:
        raise AxleSensorException("Message header {} is unvalid.".format(header))
    return d


class AxleSensor(object):
    #Defaults
    DEFAULT_THRESHOLD_ON = 1
    DEFAULT_SUM_LEN= 4
    DEFAULT_THRESHOLD_OFF=1
    DEFAULT_THRESHOLD_ERR= 2
    VALID_SUM_LEN=[2,4,8,16,32]
    #connected IO
    VBAT_PIN = IOLine.DIO0_AD0
    VBAT_SCALING = 16.63/0.718359375#230/10# reistenze v_misurata = Vbatteria*R1/(R1+R2)
    RESET_PIN = IOLine.DIO3_AD3
    SHUTDOWN_CELL_PIN = IOLine.DIO1_AD1
    IDLE_PIN_P4_0 = IOLine.DIO2_AD2


    def __init__(self, remote_axle_sensor_xbee, logger, name="",setup_io=False):
        self._xbee=remote_axle_sensor_xbee
        self._local_xbee=self._xbee.get_local_xbee_device()
        self._logger=logger.getChild(self.__class__.__name__)
        #self._rx_queque = queue.Queue()
        self.name=name
        if setup_io:
            self._xbee.set_io_configuration(self.VBAT_PIN, IOMode.ADC)
            self._xbee.set_io_configuration(self.RESET_PIN, IOMode.DIGITAL_OUT_HIGH)
            self._xbee.set_io_configuration(self.IDLE_PIN_P4_0, IOMode.DIGITAL_OUT_LOW)
            self._xbee.set_io_configuration(self.SHUTDOWN_CELL_PIN, IOMode.DIGITAL_OUT_LOW)
            self.write_changes()
            self.logger.info("Setup IO of {}.".format(self))

    def _send_rcv_status(self, msg_byte):
        """ all axle sensor have to be set in idle!
            send 1 byte and wait for 2 byte response
        """
        f_gen = unstuff_frame_from_serial_data()
        f_gen.send(None)
        self._local_xbee.set_sync_ops_timeout(0.5)
        try:
            self._local_xbee.send_data(self._xbee, bytearray([msg_byte]))
        except TimeoutException:
            s = '{} is not reachable'.format(self)
            self._logger.error(s)
            raise AxleSensorException(s)
        else:
            #wait for 2 byte response
            try:
                xbee_msg=self._local_xbee.read_data_from(self._xbee, 0.3)
            except TimeoutException:
                s = '{} is not responding.'.format(self)
                self._logger.error(s)
                raise AxleSensorException(s)
            else:
                self._logger.debug("Recieved msg {}".format(xbee_msg.data))
                frames=f_gen.send(xbee_msg.data)
                if len(frames)>1:
                    raise AxleSensorException("Too many response: {}".format(frames))
                return parse_msg(frames[0])
        finally:
            self._local_xbee.set_sync_ops_timeout(1)


    def __str__(self):
        return "Axle Sensor {}, MAC:{}".format(self.name,self.get_64bit_addr())

    def __repr__(self):
        return self.__str__()

    def get_64bit_addr(self):
        return self._xbee.get_64bit_addr()

    def reset(self):
        self._logger.info('Reset {}.'.format(self))
        self._xbee.set_dio_value(self.RESET_PIN, IOValue.LOW)
        time.sleep(1)
        self._xbee.set_dio_value(self.RESET_PIN, IOValue.HIGH)
        self.set_idle()

    def set_idle(self):
        self._logger.info('Set idle {}.'.format(self))
        self._xbee.set_dio_value(self.IDLE_PIN_P4_0, IOValue.LOW)
        time.sleep(0.1)
        self._xbee.set_dio_value(self.SHUTDOWN_CELL_PIN, IOValue.LOW)

    def set_rdy(self):
        self._logger.info('Set rdy {}.'.format(self))
        self._xbee.set_dio_value(self.IDLE_PIN_P4_0, IOValue.HIGH)
        time.sleep(0.1)
        self._xbee.set_dio_value(self.SHUTDOWN_CELL_PIN, IOValue.HIGH)

    def echo(self, i=0):
        if i not in range(8):
            raise ValueError("Echo value has to be  in {}.".format(range(8)))
        return self._send_rcv_status(MSG_ECHO+i)['echo']

    def get_vbat(self, raw=False):
        if raw:
            return self._xbee.get_adc_value(self.VBAT_PIN)* (1.2 / 1024)
        else:
            return self._xbee.get_adc_value(self.VBAT_PIN) * (1.2 / 1024) * self.VBAT_SCALING

    #msp432 settings
    def get_threshold_ERR(self):
        return self._send_rcv_status(MSG_GET_T_ERR)['thresholdERR']

    def get_threshold_ON(self):
        return self._send_rcv_status(MSG_GET_T_ON)['thresholdON']

    def get_threshold_OFF(self):
        return self._send_rcv_status(MSG_GET_T_OFF)['thresholdOFF']

    def get_sum_len(self):
        return self._send_rcv_status(MSG_GET_SUM_LEN)['sum_len']

    def set_threshold_ERR(self, seconds=None):
        if seconds is None:
            seconds= self.DEFAULT_THRESHOLD_ERR
        elif int(seconds)>5:
            raise ValueError("seconds has to be < 5.")
        return self._send_rcv_status(MSG_SET_T_ERR+int(seconds))['header']

    def set_threshold_ON(self, count=None):
        if count is None:
            count= self.DEFAULT_THRESHOLD_ON
        elif int(count)>16 or int(count)<0:
            raise ValueError("Threshold depend on sum_len. But has to be 0<threshold<16 anyway.")
        return self._send_rcv_status(MSG_SET_T_ON+int(count))['header']

    def set_threshold_OFF(self, count=None):
        if count is None:
            count= self.DEFAULT_THRESHOLD_OFF
        elif int(count)>16 or int(count)<0:
            raise ValueError("Threshold depend on sum_len. But has to be 0<threshold<16 anyway.")
        return self._send_rcv_status(MSG_SET_T_OFF+int(count))['header']

    def set_sum_len(self, len):
        if len is None:
            len = self.DEFAULT_SUM_LEN
        elif len not in self.VALID_SUM_LEN:
            raise ValueError("seconds has to be  in {}".format(str(self.VALID_SUM_LEN)))
        return self._send_rcv_status(MSG_SET_SUM_LEN + int(math.log2(len)))['header']


def init_axle_sensors_network(found_xbee, expected_axle_sensors,logger):
    xbee_addr = [d.get_64bit_addr() for d in found_xbee]
    ##
    axle_sensors=[]
    for name,addr in expected_axle_sensors.items():
        try:
            index = xbee_addr.index(addr)
        except ValueError:
            logger.warning('Axle Sensor {}, MAC: {} is missing.'.format(name,str(addr)))
        else:
            ax=AxleSensor(remote_axle_sensor_xbee=found_xbee[index],name=name,logger=logger)
            axle_sensors.append(ax)
            logger.info('{} found.'.format(ax))

    return axle_sensors


def setup_axle_sensors(axle_sensors, logger, sum_len=None,thresholdOFF=None,thresholdON=None,thresholdERR=None):
    logger.info("===Reset Axle Sensors (put in idle state and reset mcu)")
    for ax in axle_sensors:
        ax.reset()
    if sum_len is not None:
        logger.info("===Set sum len")
        for ax in axle_sensors:
            h = ax.set_sum_len(sum_len)
            logger.info("{}, set sum_len to {}, return {}.".format(ax, sum_len, h))
            sum_len = ax.get_sum_len()
            logger.info("{}, read sum_len as control. sum_len {}.".format(ax, sum_len))
            assert sum_len == sum_len
    #
    if thresholdOFF is not None:
        logger.info("===Set thresholdOFF")
        for ax in axle_sensors:
            h = ax.set_threshold_OFF(thresholdOFF)
            logger.info("{}, set thresholdOFF to {}, return {}.".format(ax, thresholdOFF, h))
            t = ax.get_threshold_OFF()
            logger.info("{}, read thresholdOFF as control. thresholdOFF {}.".format(ax, t))
            assert t == thresholdOFF
    #
    if thresholdON is not None:
        logger.info("===Set thresholdON")
        for ax in axle_sensors:
            h = ax.set_threshold_ON(thresholdON)
            logger.info("{}, set thresholdON to {}, return {}.".format(ax, thresholdON, h))
            t = ax.get_threshold_ON()
            logger.info("{}, read thresholdON as control. thresholdON {}.".format(ax, t))
            assert t == thresholdON

    if thresholdERR is not None:
        logger.info("===Set thresholdERR")
        for ax in axle_sensors:
            h = ax.set_threshold_ERR(thresholdERR)
            logger.info("{}, set thresholdERR to {}, return {}.".format(ax, thresholdERR, h))
            t = ax.get_threshold_ERR()
            logger.info("{}, read thresholdERR as control. thresholdERR {}.".format(ax, t))
            assert t == thresholdERR

    logger.info("===Log VBAT")
    for ax in axle_sensors:
        v = ax.get_vbat()
        vr = ax.get_vbat(raw=True)
        logger.info("{}, vbat {},  vbat raw {}.".format(ax, v, vr))

    logger.info("=================================")
    logger.info("=== Put Axle Sensor in rdy state.")
    for ax in axle_sensors:
        ax.set_rdy()

