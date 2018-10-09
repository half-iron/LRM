from digi.xbee.devices import XBeeDevice
import time
from pyLRM.axle_sensor import parse_msg, TrainPassby, unstuff_frame_from_serial_data,init_axle_sensors_network
import importlib, logging,sys
from datetime import datetime

import pyLRM.config as config

from queue import Queue
import json

#config = importlib.import_module('config')
logger = logging.getLogger()
loggerHandler2 = logging.StreamHandler(sys.stdout)
logger.addHandler(loggerHandler2)

#########################################

#define globals variables
g_msg_Q = Queue(100)

g_unstuff_frame = unstuff_frame_from_serial_data() #generator used only in xbee thread(not thread safe!)
g_unstuff_frame.send(None)

def data_receive_callback(xbee_message):
    """unstuuff frames parse msg and log message"""
    timestamp = datetime.now()
    from_address = xbee_message.remote_device.get_64bit_addr()
    # if from an axle sensor
    frames = g_unstuff_frame.send(xbee_message.data)
    #logger.debug("{}".format(frames))

    for frame in frames:
        try:
            msg = parse_msg(frame)
            msg.update({'timestamp':timestamp,'from_address':from_address})
            g_msg_Q.put(msg)
            #
        except Exception as e:
            logger.critical(e)

if __name__=="__main__":
    ##########################

    coord_xbee = XBeeDevice(port=config.xbee_coordinator['port'], baud_rate=config.xbee_coordinator['baud_rate'])
    logger.info("Open Xbee {port} baud {baud_rate}".format(**config.xbee_coordinator))
    coord_xbee.open()
    coord_xbee.flush_queues()

    xnet = coord_xbee.get_network()
    xnet.set_discovery_timeout(5)
    xnet.clear()
    logger.info("Scan Network")
    xnet.start_discovery_process()
    while xnet.is_discovery_running():
        time.sleep(0.5)
        #
    logger.info("Init Axle Sensors")
    axle_sensors=init_axle_sensors_network(xnet, config)
    logger.info("Sleep and hard reset axle sensors")

    for ax in axle_sensors:
        ax.reset()
        ax.sleep()

    coord_xbee.add_data_received_callback(data_receive_callback)