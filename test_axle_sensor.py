import pathlib
from serial.tools import list_ports
from digi.xbee.devices import XBeeDevice
import time
from pyLRM.axle_sensor import parse_msg, unstuff_frame_from_serial_data, init_axle_sensors_network,setup_axle_sensors
from datetime import datetime
import pyLRM.config as config
from pyLRM.config import xbee_axle_sensors_name_from_addr
from pyLRM.passby import TrainPassby
from pyLRM.logging_handler import init_logger, ax_sensor_log_gen
import argparse
from queue import Queue

def serial_port_by_vid_pid(vid,pid,logger):
    """
    search and return serial port name given vendor and product id
    :param vid: vendor id
    :param pid: product id
    :param logger:
    :return: portname
    """
    logger.debug("Search serial device with vid:{} and pid:{}.".format(vid,pid))
    for p in list_ports.comports():
        if (p.vid,p.pid) ==(vid,pid):
            logger.debug('Found serial device {} with device name {}.'.format(p.description,p.device))
            return p.device
    logger.debug("No serial device found.")
    raise FileNotFoundError('serial port device file not found.')


def data_receive_callback(xbee_message):
    """unstuff frames parse msg and log message"""
    from_address = xbee_message.remote_device.get_64bit_addr()
    frames = g_unstuff_frame.send(xbee_message.data)
    for frame in frames:
        try:
            msg = parse_msg(frame)
            g_msg_Q.put([msg, from_address, datetime.now()])
            #
        except Exception as e:
            logger.critical(e)

if __name__=="__main__":

    parser = argparse.ArgumentParser(prog='PROG',
                                     description='Sucht Xbee network für axle_sensors und prüft die funktionalität.')
    parser.add_argument('-PC', action='store_true', help='Falls den test auf PC mit Xbee modul läuft.')
    parser.add_argument('-name', type=str,
                        help='A folder containing passby files and logs will be created. If exists log are appended.',
                        default='test')
    parser.add_argument('-log_debug', action='store_true', help='Set logger to debug level.')
    parser.add_argument('-ax_sensor_settings', nargs=4,
                        default= config.AX_SETTINGS_DEFAULTS,
                        type=int,
                        help='Pass AxleSensorSettings: \n sum_len, thresholdON, thresholdOFF, thresholdERR.\n Default: {}'.format(config.AX_SETTINGS_DEFAULTS)
                        )
    parser.add_argument('-passby',
                        action='store_true',
                        help='Enable passby'
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
                         level=("DEBUG" if args.log_debug else "INFO"),
                         mail=False)


    logger.info("==============")

    try:
        logger.info("===Init Xbee coordinator.")
        if args.PC:
            try:
                port = serial_port_by_vid_pid(*config.xbee_test["serial_adapter_id"], logger)
            except FileNotFoundError as e:
                logger.critical('Xbee on USB2SERIAL adapter not found.')
                raise e
            else:
                logger.info("Open Xbee on USB2SERIAL adapter on port {} with baud {}".format(port, config.xbee_test[
                    "baud_rate"]))
                coord_xbee = XBeeDevice(port=port, baud_rate=config.xbee_test['baud_rate'])
        else:
            logger.info("Open Xbee on BBG at {port} with baud {baud_rate}.".format(**config.xbee_BBG))
            coord_xbee = XBeeDevice(port=config.xbee_BBG['port'], baud_rate=config.xbee_BBG['baud_rate'])

        # open xbe
        coord_xbee.open()
        coord_xbee.flush_queues()

        # scan network
        xnet = coord_xbee.get_network()
        xnet.set_discovery_timeout(5)
        xnet.clear()
        logger.info("===Scan Network")
        xnet.start_discovery_process()

        while xnet.is_discovery_running():
            time.sleep(0.5)
            #
        axle_sensors = init_axle_sensors_network(xnet.get_devices(), config.xbee_axle_sensors, logger)

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

        if args.passby:
            npassby = 0
            clear = False
            passby = TrainPassby(axle_sensors_names=list(config.xbee_axle_sensors_names),
                                 stop_delay=args.stop_delay, ax_counter_low_err=4)

        logger.info("Add callback.")
        coord_xbee.add_data_received_callback(data_receive_callback)
        ##
        logger.info("Poll for data waiting for axle events.")

        while True:
            time.sleep(0.001)
            if not g_msg_Q.empty():
                msg, from_address, timestamp = g_msg_Q.get()
                ax_name = xbee_axle_sensors_name_from_addr(from_address)
                ax_log_gen.send([msg, from_address, timestamp, clear])

                if args.passby:
                    if clear:
                        clear = False
                    passby.add_axle_data(**{**msg, 'ax_name': ax_name, 'timestamp': timestamp})
            ##start stop rec
            if args.passby:
                if passby.rec():
                    if not REC:
                        REC = True
                        passby.set_rec_start_time()
                        logger.info("Start rec {}.".format(passby._name))
                        passby.set_rec_start_time()
                else:
                    if REC:
                        REC = False
                        passby.set_rec_stop_time()
                        if passby.is_error:
                            logger.error("Stop rec {}.Passby has error".format(passby._name))
                        else:
                            logger.info("Stop rec {}.".format(passby._name))
                        # new passby
                        npassby += 1
                        passby = TrainPassby(axle_sensors_names=list(config.xbee_axle_sensors_names),
                                             stop_delay=15, ax_counter_low_err=4)
                        clear = True
                    elif passby.is_error:
                        passby.export(path=path)
                        logger.error("Error passby {}. No REC.Reset.".format(passby._name))
                        npassby += 1
                        passby = TrainPassby(axle_sensors_names=list(config.xbee_axle_sensors_names),
                                             stop_delay=args.stop_delay, ax_counter_low_err=4)
                        clear = True

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
        logger.info("==============")
