from digi.xbee.devices import XBeeDevice
import time
from axle_sensor import parse_msg,TrainPassby, unstuff_frame_from_serial_data,init_axle_sensors_network
from logging_handler import init_logger

import pathlib
import importlib
from datetime import datetime
import argparse
import os,sys
import shutil
from mesurement_device import xl2_setup_measurement, xl2_init,INITIATE
from queue import Queue
import json

config = importlib.import_module('config')

#esclude pezzi di codice codice 0 non esclude niente
DEBUG_LEVEL=0

if DEBUG_LEVEL<=1:
#argparsing
    parser = argparse.ArgumentParser(prog='PROG', description='!!!')

    parser.add_argument('-name', type=str,
                        help='Name of the measuremet session. A folder containing measurement session files will be created.',
                        default='auto')
    parser.add_argument('-option',choices=['normal','append','replace'], default='normal')
    parser.add_argument('-conf-file',type=str, default='config.py')
    parser.add_argument('-discover',type=str, default='config.py')



    args=parser.parse_args()
    #import config file
    if args.name=='auto':
        PATH0=pathlib.Path().home().joinpath("Messung_{:%Y_%m_%d_%Hh%Mm}".format(datetime.now()))
    else:
        PATH0= pathlib.Path(args.name).absolute()
    option = args.option

else:#DEBUG
    PATH0 = pathlib.Path('test')
    option = 'replace'


if option=='replace':
    if PATH0.exists():
        shutil.rmtree(PATH0.as_posix())
    PATH0.mkdir()
elif option=='append':
    os.chdir(PATH0)
elif option=='normal':
    PATH0.mkdir()

passbyPath=PATH0.joinpath('passby')
passbyPath.mkdir()

#########################################
#main logger
logger,g_DataLogger=init_logger(__name__,PATH0)


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
            g_DataLogger.info("{}".format(json.dumps(msg, sort_keys=True, default=str)))
        except Exception as e:
            logger.critical(e)

if __name__=="__main__":
    ##########################

    logger.info("Start System")

    if DEBUG_LEVEL<=2:
        logger.info("Init XL2")
        xl2 = xl2_init(logger)
        xl2_setup_measurement(xl2,logger)
    else: #DEBUG_LEVEL>2
        xl2=None

    logger.info("Init XbeeMaster device at port {}.".format(config.xbee_coordinator['port']))

    try:

        coord_xbee = XBeeDevice(port=config.xbee_coordinator['port'], baud_rate=config.xbee_coordinator['baud_rate'])
        # flow_control=config.xbee_coordinator['flow_control'])
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

        #############################
        ##START measurement main loop
        logger.info("wakeup sensors")
        for ax in axle_sensors:
            ax.wake_up()
        timestamp = datetime.now()
        logger.info("Measurement started at timestamp {}.".format(timestamp))
        g_DataLogger.info("Measurement started at timestamp {}.".format(timestamp))
        ###############
        #  MAIN LOOP  #
        ###############
        ###############
        npassby = 0
        passby = TrainPassby(npassby)
        REC=False

        while 1:

            time.sleep(0.001)
            if passby.start_rec:
                if not REC:
                    REC = True
                    logger.info("Start measurement, passby n: {}.".format(npassby))
                    xl2.serial_message(INITIATE.START())
                    passby.set_rec_start_time()
                    passby.set_xl2_BBG_sync_time(xl2.get_datetime())
                    # if measurement has started
                if passby.stop_rec:
                    if passby.timed_out:
                        logger.warning("stop by timeout")
                    if REC:
                        REC = False
                        logger.info("Stop measurement, passby n: {}.".format(npassby))
                        xl2.serial_message(INITIATE.STOP())
                        passby.set_rec_stop_time()
                        # wetter
                        passby.add_weather_info()
                        passby.export(passbyPath)
                        #todo if timeout error
                        if passby.timed_out:
                            logger.warning("reset axle sensors")
                            for ax in axle_sensors:
                                ax.reset()
                            #reset axle sensor
                        # reset passby
                        npassby += 1
                        passby = TrainPassby(npassby)

            ##reset axle sensor if timeout occurr


            if not g_msg_Q.empty():
                msg = g_msg_Q.get()
                passby.add_axle_data(**msg)

            #log state if necessary

        ###############
        ###############
    except KeyboardInterrupt:
        logger.warning('Exit by KeyboardInterrupt')

    except Exception as e:
        logger.critical('Exit measurement at {}.\n{}.'.format(datetime.now(),str(e)))
    finally:
        try:
            if REC:
                logger.info('Stop_measurement')
                xl2.serial_message(INITIATE.STOP())
                passby.export(passbyPath, force=True)
            xl2.reset()
        except:
            pass

        logger.info('Try to put sensors in sleep mode')
        try:
            for ax in axle_sensors:
                ax.sleep()
        except:
            logger.error('Failed')

        #close serial connections
        logger.error('Close serial connections to XL2 and xbee')
        try:
            xl2.close()
            coord_xbee.close()
        except:
            logger.error('Failed')

        logger.info('Exit Measurement\n##############')