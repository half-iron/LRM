from digi.xbee.devices import XBeeDevice
import time
from pyLRM.axle_sensor import parse_msg, unstuff_frame_from_serial_data, init_axle_sensors_network
from pyLRM.tools import serial_port_by_vid_pid
from datetime import datetime
import pyLRM.config as config
from pyLRM.logging_handler import init_logger
import argparse


def data_receive_callback(xbee_message):
    """unstuff frames parse msg and log message"""
    timestamp = datetime.now()
    from_address = xbee_message.remote_device.get_64bit_addr()
    frames = g_unstuff_frame.send(xbee_message.data)
    parsed_f=[parse_msg(f) for f in frames]
    logger.info("from {}: {},raw : {}.".format(from_address,
                                                  str(parsed_f), xbee_message.data))


if __name__=="__main__":

    AX_SETTINGS_DEFAULTS= [8,2,2,1]

    parser = argparse.ArgumentParser(prog='PROG', description ='Sucht Xbee network für axle_sensors und Prüft die funktionalität.')

    parser.add_argument('-BBG', action='store_true',  help='Forciert BBG==True.')
    parser.add_argument('-nolog', action='store_true', help='No file logging.')
    parser.add_argument('-log_debug', action='store_true', help='Set logger to debug level.')
    parser.add_argument('-ax_sensor_settings', nargs=4,
                        default= AX_SETTINGS_DEFAULTS,
                        type=int,
                        help='Pass AxleSensorSettings: \n sum_len, thresholdON, thresholdOFF, thresholdERR.\n Default: {}'.format(AX_SETTINGS_DEFAULTS)
                        )

    args = parser.parse_args()
    sum_len, thresholdON, thresholdOFF, thresholdERR = args.ax_sensor_settings

    logger = init_logger("test_axle_sensor",
                         file=(not args.nolog),
                         level=("DEBUG" if args.log_debug else "INFO"),
                         mail=False)

    g_unstuff_frame = unstuff_frame_from_serial_data()  # generator used only in xbee thread(not thread safe!)
    g_unstuff_frame.send(None)

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
        # reset axle_sensors
        logger.info("===Reset Axle Sensors (put in idle state and reset mcu)")
        for ax in axle_sensors:
            ax.reset()

        logger.info("===Test echo axle sensors")
        for i, ax in enumerate(axle_sensors):
            echoback = ax.echo(i)
            logger.info("{}, echo value {}, return {}.".format(ax, i, echoback))
            assert echoback==i
        logger.info("=== Axle Sensor settings: sum_len {}, thresholdON {}, thresholdOFF {}, thresholdERR {}.".format(sum_len, thresholdON, thresholdOFF, thresholdERR))
        #
        logger.info("===Test set sum len")
        for ax in axle_sensors:
            sum_len_d = ax.get_sum_len()
            logger.info("{}, sum_len {}, default {}.".format(ax, sum_len_d, ax.DEFAULT_SUM_LEN))
            assert sum_len_d==ax.DEFAULT_SUM_LEN
            h = ax.set_sum_len(sum_len)
            logger.info("{}, set sum_len to {}, return {}.".format(ax, sum_len, h))
            sum_len = ax.get_sum_len()
            logger.info("{}, read sum_len as control. sum_len {}.".format(ax, sum_len))
            assert sum_len==sum_len
        #
        logger.info("===Test set thresholdOFF")
        for ax in axle_sensors:
            t = ax.get_threshold_OFF()
            logger.info("{}, thresholdOFF {}, default {}.".format(ax, t, ax.DEFAULT_THRESHOLD_OFF))
            assert t==ax.DEFAULT_THRESHOLD_OFF
            h = ax.set_threshold_OFF(thresholdOFF)
            logger.info("{}, set thresholdOFF to {}, return {}.".format(ax, thresholdOFF, h))
            t = ax.get_threshold_OFF()
            logger.info("{}, read thresholdOFF as control. thresholdOFF {}.".format(ax, t))
            assert t==thresholdOFF
        #
        logger.info("===Test set thresholdON")
        for ax in axle_sensors:
            t = ax.get_threshold_ON()
            logger.info("{}, thresholdON {}, default {}.".format(ax, t, ax.DEFAULT_THRESHOLD_ON))
            assert t == ax.DEFAULT_THRESHOLD_ON
            h = ax.set_threshold_ON(thresholdON)
            logger.info("{}, set thresholdON to {}, return {}.".format(ax, thresholdON, h))
            t = ax.get_threshold_ON()
            logger.info("{}, read thresholdON as control. thresholdON {}.".format(ax, t))
            assert t == thresholdON

        logger.info("===Test set thresholdERR")
        for ax in axle_sensors:
            t = ax.get_threshold_ERR()
            logger.info("{}, thresholdERR {}, default {}.".format(ax, t, ax.DEFAULT_THRESHOLD_ERR))
            assert t == ax.DEFAULT_THRESHOLD_ERR
            h = ax.set_threshold_ERR(thresholdERR)
            logger.info("{}, set thresholdERR to {}, return {}.".format(ax, thresholdERR, h))
            t = ax.get_threshold_ERR()
            logger.info("{}, read thresholdERR as control. thresholdERR {}.".format(ax, t))
            assert t == thresholdERR

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
        while True:
            time.sleep(0.005)

    except KeyboardInterrupt:
        logger.warning('===Exit by KeyboardInterrupt')

    except Exception as e:
        logger.error('===Exit test_axle_sensors.py wegen Exception.\n{}.'.format(str(e)))

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
