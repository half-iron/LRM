from digi.xbee.devices import XBeeDevice
import time
import pathlib
from pyLRM.axle_sensor import parse_msg, unstuff_frame_from_serial_data, init_axle_sensors_network,setup_axle_sensors
from datetime import datetime
import pyLRM.config as config
from pyLRM.config import xbee_axle_sensors_name_from_addr
from pyLRM.passby import TrainPassby
from pyLRM.logging_handler import init_logger, ax_sensor_log_gen,init_mail_logger
import argparse
from queue import Queue
from ntixl2 import XL2SLM_serial
from ntixl2.message import INITIATE



def main(logger,profile,stop_delay,passbypath, axsettings,stop_time):

    logger.info("========================")
    logger.info("===Init XL2.")

    try:
        xl2 = XL2SLM_serial.from_usb_id(ids=config.XL2['serial_usb_id'],logger=logger)
        xl2.open()
        logger.info("Open XL2 ok.")
        logger.info("Setup XL2 measurement profile.")
        xl2.select_profile(profile=profile)


        logger.info("===Init Xbee coordinator.")
        logger.info("Open Xbee on BBG at {port} with baud {baud_rate}.".format(**config.xbee_BBG))
        coord_xbee = XBeeDevice(port=config.xbee_BBG['port'], baud_rate=config.xbee_BBG['baud_rate'])

        #open xbe
        coord_xbee.open()
        coord_xbee.flush_queues()

        #scan network
        xnet = coord_xbee.get_network()
        xnet.set_discovery_timeout(5)
        xnet.clear()
        logger.info("===Scan Xbee Network")
        xnet.start_discovery_process()

        while xnet.is_discovery_running():
            time.sleep(0.5)
            #
        axle_sensors = init_axle_sensors_network(xnet.get_devices(), config.xbee_axle_sensors,logger)

        # setup axle_sensors
        sum_len, thresholdON, thresholdOFF, thresholdERR = axsettings
        setup_axle_sensors(axle_sensors, logger,
                           sum_len=sum_len,
                           thresholdOFF=thresholdOFF,
                           thresholdON=thresholdON,
                           thresholdERR=thresholdERR)
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
        clear_log_counter = False
        passby = TrainPassby(axle_sensors_names=list(config.xbee_axle_sensors_names),
                             stop_delay=stop_delay, ax_counter_low_err=4)
        logger.info("Add callback.")
        coord_xbee.add_data_received_callback(data_receive_callback)
        ##
        logger.info("Poll for data waiting for axle events.")
        REC = False
        while True:
            time.sleep(0.001)
            if not g_msg_Q.empty():
                msg, from_address, timestamp= g_msg_Q.get()
                ax_name = xbee_axle_sensors_name_from_addr(from_address)
                ax_log_gen.send([msg, from_address, timestamp, clear_log_counter])
                if clear_log_counter:
                    clear_log_counter =False
                passby.add_axle_data(**{**msg,'ax_name':ax_name,'timestamp':timestamp})
            ##start stop rec
            if passby.rec():
                if not REC:
                    REC=True
                    try:
                        xl2.serial_message(INITIATE.START())
                    except Exception as e:
                        logger.error("Error start.{}.".format(str(e)))
                        raise e
                    else:
                        passby.set_rec_start_time()
                        logger.info("Start rec {}.".format(passby._name))
            else:
                if REC:
                    REC=False
                    try:
                        xl2.serial_message(INITIATE.STOP())
                    except Exception as e:
                        logger.error("Error  stop.{}.".format(str(e)))
                        raise e
                    else:
                        passby.set_rec_stop_time()

                    time.sleep(2)
                    try:
                        xl2time=xl2.get_datetime()
                    except Exception as e:
                        logger.error("Error xl2.get_datetime. Error{}.".format(str(e)))
                        try:
                            xl2time=xl2.get_datetime()
                        except Exception as e:
                            logger.error("Error N.2 xl2.get_datetime. Error{}.".format(str(e)))
                            raise e

                    passby.set_xl2_BBG_sync_time(xl2time)
                    passby.export(path=passbypath)
                    if passby.is_error:
                        logger.error("Stop rec {}.Passby has error".format(passby._name))
                    else:
                        logger.info("Stop rec {}.".format(passby._name))
                    #new passby
                    npassby += 1
                    passby = TrainPassby(axle_sensors_names=list(config.xbee_axle_sensors_names),
                                         stop_delay=15, ax_counter_low_err=4)
                    clear_log_counter=True
                elif passby.is_error:
                    passby.export(path=passbypath)
                    logger.error("Error passby {}. No REC. Reset.".format(passby._name))
                    npassby += 1
                    passby = TrainPassby( axle_sensors_names=list(config.xbee_axle_sensors_names),
                                         stop_delay=stop_delay, ax_counter_low_err=4)
                    clear_log_counter = True

                elif datetime.now()>stop_time:
                    logger.warning("Exit measuremet . Reached stop time.")
                    break

    except KeyboardInterrupt as e:
        logger.warning('===Exit by KeyboardInterrupt')

    except Exception as e:
        logger.error('===Exit {} wegen Exception.\n{}.'.format(pathlib.Path(__file__).name, str(e)))
        raise e
    finally:
        logger.info('Put axle_sensors in idle state.')
        for ax in axle_sensors:
            ax.set_idle()
        # close serial connections
        logger.info('Close xbee serial connection.')
        coord_xbee.close()
        try:
            if REC:
                logger.error('Stop_measurement')
                xl2.serial_message(INITIATE.STOP())
                passby.export(passbypath, force=True)
            xl2.reset()
        finally:
            logger.info('Close xl2 serial connection.')
            xl2.close()




if __name__=="__main__":

    parser = argparse.ArgumentParser(prog='PROG', description ='implementiert die Messung.')
    parser.add_argument('-name', type=str,
                        help='Name of the measuremet session. A folder containing measurement session files will be created. If exists log are appended.',
                        default='test')
    parser.add_argument('-log_debug', action='store_true', help='Set logger to debug level.')
    parser.add_argument('-ax_sensor_settings', nargs=4,
                        default= config.AX_SETTINGS_DEFAULTS,
                        type=int,
                        help='Pass AxleSensorSettings: \n sum_len, thresholdON, thresholdOFF, thresholdERR.\n Default: {}'.format(config.AX_SETTINGS_DEFAULTS)
                        )
    parser.add_argument('-stop_delay',
                        default= config.STOP_DELAY,
                        type=int,
                        help='Stop passby after {} seconds.'.format(config.STOP_DELAY)
                        )

    args = parser.parse_args()

    path = pathlib.Path(args.name).absolute()
    path.mkdir(exist_ok=True)


    logger = init_logger(pathlib.Path(__file__).name.split(".py")[0],
                         filepath=path,
                         level=("DEBUG" if args.log_debug else "INFO"))

    maillogger = init_mail_logger("mail")


    logger.info("==============")
    maillogger.info("Start {}.".format(args.name))
    i = 0
    while i<10:
        try:
            r = main(logger,profile=config.PROFILE,stop_delay=args.stop_delay, passbypath=path,
                 axsettings=args.ax_sensor_settings,stop_time=config.STOP)

        except Exception as e:
            i+=1
            logger.exception("Iteration {}.".format(i))
            maillogger.error("Iteration {:d}".format(i), exc_info=True)
            time.sleep(10)
        else:
            maillogger.critical("Stop {}.".format(args.name))
            break
    logger.info("================")
