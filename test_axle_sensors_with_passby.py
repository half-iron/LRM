from digi.xbee.devices import XBeeDevice
import time
from pyLRM.axle_sensor import parse_msg, unstuff_frame_from_serial_data, init_axle_sensors_network,setup_axle_sensors
from pyLRM.tools import serial_port_by_vid_pid
from datetime import datetime
import pyLRM.config as config
from pyLRM.config import xbee_axle_sensors_name_from_addr,xbee_axle_sensors
from pyLRM.passby import TrainPassby
from pyLRM.logging_handler import init_logger,ax_sensor_log_gen
import argparse
from queue import Queue
import pathlib

AX_SETTINGS_DEFAULTS = [16, 8, 2, 1]
testpath=pathlib.Path('test')
STOP_DELAY=15
if __name__=="__main__":


    parser = argparse.ArgumentParser(prog='PROG', description ='Sucht Xbee network für axle_sensors und Prüft die funktionalität.')

    parser.add_argument('-BBG', action='store_true',  help='Forciert BBG==True.')
    parser.add_argument('-no_log', action='store_true', help='No file logging.')
    parser.add_argument('-log_debug', action='store_true', help='Set logger to debug level.')
    parser.add_argument('-ax_sensor_settings', nargs=4,
                        default= AX_SETTINGS_DEFAULTS,
                        type=int,
                        help='Pass AxleSensorSettings: \n sum_len, thresholdON, thresholdOFF, thresholdERR.\n Default: {}'.format(AX_SETTINGS_DEFAULTS)
                        )

    args = parser.parse_args()

    logger = init_logger("test_axle_sensor",
                         file=(not args.no_log),
                         filepath=testpath,
                         level=("DEBUG" if args.log_debug else "INFO"),
                         mail=False)

    logger.info("Run test_axle_sensor.py.")
    logger.info("========================")
    try:
        logger.info("===Init Xbee coordinator.")
        if False if args.BBG else (not config.BBG):
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

        # setup axle_sensors
        sum_len, thresholdON, thresholdOFF, thresholdERR = args.ax_sensor_settings
        setup_axle_sensors(axle_sensors, logger,
                           sum_len=sum_len,
                           thresholdOFF=thresholdOFF,
                           thresholdON=thresholdON,
                           thresholdERR=thresholdERR)
        ##


        # define globals variables
        g_msg_Q = Queue(100)
        g_unstuff_frame = unstuff_frame_from_serial_data()  # generator used only in xbee thread(not thread safe!)
        g_unstuff_frame.send(None)
        # init log generator
        ax_log_gen = ax_sensor_log_gen(logger, config.xbee_axle_sensors_names)
        ax_log_gen.send(None)
        #
        def data_receive_callback(xbee_message):
            """unstuuff frames parse msg and log message"""
            from_address = xbee_message.remote_device.get_64bit_addr()
            frames = g_unstuff_frame.send(xbee_message.data)
            for frame in frames:
                try:
                    msg = parse_msg(frame)
                    g_msg_Q.put([msg, from_address, datetime.now()])
                    #
                except Exception as e:
                    logger.critical(e)

        npassby = 0
        clear = False
        passby = TrainPassby(rec_n=npassby, axle_sensors_names=list(config.xbee_axle_sensors_names),
                             stop_delay=STOP_DELAY, ax_counter_low_err=4)
        logger.info("Add callback.")
        coord_xbee.add_data_received_callback(data_receive_callback)
        ##
        logger.info("Poll for data waiting for axle events.")
        REC = False
        ERROR=False
        while True:
            time.sleep(0.001)
            if not g_msg_Q.empty():
                msg, from_address, timestamp= g_msg_Q.get()
                ax_name=xbee_axle_sensors_name_from_addr(from_address)
                ax_log_gen.send([msg, from_address, timestamp, clear])
                if clear:
                    clear =False
                passby.add_axle_data(**{**msg,'ax_name':ax_name,'timestamp':timestamp})
            ##start stop rec
            if passby.rec():
                if not REC:
                    REC=True
                    passby.set_rec_start_time()
                    logger.info("Start rec {}.".format(passby._name))
            else:
                if REC:
                    REC=False
                    passby.set_rec_stop_time()
                    passby.export(path=testpath)
                    if passby.is_error:
                        logger.info("Stop rec {}.Passby has error".format(passby._name))
                    else:
                        logger.info("Stop rec {}.".format(passby._name))
                    #new passby
                    npassby += 1
                    passby = TrainPassby(rec_n=npassby, axle_sensors_names=list(config.xbee_axle_sensors_names),
                                         stop_delay=15, ax_counter_low_err=4)
                    clear=True
                elif passby.is_error:
                    passby.export(path=testpath)
                    logger.info("Error passby {}. No REC.Reset.".format(passby._name))                    # new passby
                    npassby += 1
                    passby = TrainPassby(rec_n=npassby, axle_sensors_names=list(config.xbee_axle_sensors_names),
                                         stop_delay=STOP_DELAY, ax_counter_low_err=4)
                    clear = True

    except KeyboardInterrupt:
        logger.warning('===Exit by KeyboardInterrupt')

    except Exception as e:
        logger.error('===Exit test_axle_sensors.py wegen Exception.\n{}.'.format(str(e)))
        raise e
    finally:
        for ax in axle_sensors:
            try:
                ax.set_idle()
            except:
                logger.error('set_idle {} failed.'.format(ax))
        # close serial connections
        logger.info('Close coord_xbee serial connection.')
        try:
            coord_xbee.close()
        except:
            logger.error('Close coord_xbee failed.')

        logger.info('Exit test_axle_sensor.py.')
