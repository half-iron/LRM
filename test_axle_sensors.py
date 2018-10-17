from digi.xbee.devices import XBeeDevice
import time
from pyLRM.axle_sensor import parse_msg, unstuff_frame_from_serial_data, init_axle_sensors_network
from pyLRM.tools import serial_port_by_vid_pid
from datetime import datetime
import pyLRM.config as config
from pyLRM.logging_handler import init_logger

#########################################
logger= init_logger("test_axle_sensor",level='INFO', mail=False)

g_unstuff_frame = unstuff_frame_from_serial_data() #generator used only in xbee thread(not thread safe!)
g_unstuff_frame.send(None)

def data_receive_callback(xbee_message):
    """unstuff frames parse msg and log message"""
    timestamp = datetime.now()
    from_address = xbee_message.remote_device.get_64bit_addr()
    frames = g_unstuff_frame.send(xbee_message.data)
    parsed_f=[parse_msg(f) for f in frames]
    logger.info("{} from {}: {},raw : {}.".format(str(timestamp),from_address,
                                                  str(parsed_f), xbee_message.data))


#if __name__=="__main__":
##########################
logger.info("Run test_axle_sensor.py.")
logger.info("========================")

logger.info("===Init Xbee coordinator.")
if not config.BBG:
    try:
        port = serial_port_by_vid_pid(*config.xbee_test["serial_adapter_id"],logger)
    except FileNotFoundError as e:
        logger.critical('Xbee on USB2SERIAL adapter not found.')
        raise e
    else:
        logger.info("Open Xbee on USB2SERIAL adapter on port {} with baud {}".format(port,config.xbee_test["baud_rate"]))
        coord_xbee = XBeeDevice(port=port, baud_rate=config.xbee_test['baud_rate'])
else:
    logger.info("Open Xbee on BBG at {port} with baud {baud_rate}.".format(**config.xbee_BBG))
    coord_xbee = XBeeDevice(port=config.xbee_BBG['port'], baud_rate=config.xbee_BBG['baud_rate'])

#open xbe
coord_xbee.open()
coord_xbee.flush_queues()

#scan network
xnet = coord_xbee.get_network()
xnet.set_discovery_timeout(5)
xnet.clear()
logger.info("===Scan Network")
xnet.start_discovery_process()

while xnet.is_discovery_running():
    time.sleep(0.5)
    #
axle_sensors = init_axle_sensors_network(xnet.get_devices(), config.xbee_axle_sensors,logger)
# reset axle_sensors
logger.info("===Reset Axle Sensors (put in idle state and reset mcu)")
for ax in axle_sensors:
    ax.reset()

logger.info("===Test echo axle sensors")
for i, ax in enumerate(axle_sensors):
    echoback = ax.echo(i)
    logger.info("{}, echo value {}, return {}.".format(ax, i, echoback))
    assert echoback==i

logger.info("===Test set sum len")
for ax in axle_sensors:
    sum_len = ax.get_sum_len()
    logger.info("{}, sum_len {}, default {}.".format(ax, sum_len,ax.DEFAULT_SUM_LEN))
    assert sum_len==ax.DEFAULT_SUM_LEN
    h = ax.set_sum_len(32)
    logger.info("{}, set sum_len to {}, return {}.".format(ax, 32, h))
    sum_len = ax.get_sum_len()
    logger.info("{}, read sum_len as control. sum_len {}.".format(ax, sum_len))
    assert sum_len==32

logger.info("===Test set thresholdOFF")
for ax in axle_sensors:
    t = ax.get_threshold_OFF()
    logger.info("{}, thresholdOFF {}, default {}.".format(ax, t, ax.DEFAULT_THRESHOLD_OFF))
    assert t==ax.DEFAULT_THRESHOLD_OFF
    h = ax.set_threshold_OFF(4)
    logger.info("{}, set thresholdOFF to {}, return {}.".format(ax, 4, h))
    t = ax.get_threshold_OFF()
    logger.info("{}, read thresholdOFF as control. thresholdOFF {}.".format(ax, t))
    assert t==4

logger.info("===Test set thresholdON")
for ax in axle_sensors:
    t = ax.get_threshold_ON()
    logger.info("{}, thresholdON {}, default {}.".format(ax, t, ax.DEFAULT_THRESHOLD_ON))
    assert t == ax.DEFAULT_THRESHOLD_ON
    h = ax.set_threshold_ON(5)
    logger.info("{}, set thresholdON to {}, return {}.".format(ax, 5, h))
    t = ax.get_threshold_ON()
    logger.info("{}, read thresholdON as control. thresholdON {}.".format(ax, t))
    assert t == 5

logger.info("===Test set thresholdERR")
for ax in axle_sensors:
    t = ax.get_threshold_ERR()
    logger.info("{}, thresholdERR {}, default {}.".format(ax, t, ax.DEFAULT_THRESHOLD_ERR))
    assert t == ax.DEFAULT_THRESHOLD_ERR
    h = ax.set_threshold_ERR(3)
    logger.info("{}, set thresholdERR to {}, return {}.".format(ax, 3, h))
    t = ax.get_threshold_ERR()
    logger.info("{}, read thresholdERR as control. thresholdERR {}.".format(ax, t))
    assert t == 3

logger.info("===Test get VBAT")
for ax in axle_sensors:
    v = ax.get_vbat()
    vr = ax.get_vbat(raw=True)
    logger.info("{}, vbat {},  vbat raw {}.".format(ax, v, vr))


logger.info("=================================")
logger.info("=== Put Axle Sensor in rdy state.")
for ax in axle_sensors:
    ax.set_rdy()

logger.info("Add callback to xbee_coordinator and wait for axle events.")
#add callback to print parsed recieved frames from axle_sensord
coord_xbee.add_data_received_callback(data_receive_callback)
