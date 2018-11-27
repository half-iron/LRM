from logging.handlers import SMTPHandler
import logging
import smtplib
from email.utils import formatdate
import sys
import pathlib
import pyLRM.config as config
import parse,datetime

FORMATTER = logging.Formatter('%(asctime)s | %(name)s |  %(levelname)s: %(message)s')
FORMATTER2 = logging.Formatter('%(name)s |  %(levelname)s: %(message)s')

def init_logger(name="", level = "INFO", filepath=pathlib.Path(), systdout=True, file=True):
    logger = logging.getLogger("LRM_{}".format(name))
    logger.setLevel(level)

    if file:
        # add file handler
        messystemFilePath = filepath.joinpath("LRM_{}.log".format(name))
        messystemFileLoggerHandler = logging.FileHandler(messystemFilePath.as_posix())
        messystemFileLoggerHandler.setFormatter(FORMATTER2)
        # add file handler
        logger.addHandler(messystemFileLoggerHandler)

    if systdout:
        #standardout handler
        stdoutLoggerHandler = logging.StreamHandler(sys.stdout)
        stdoutLoggerHandler.setFormatter(FORMATTER2)
        logger.addHandler(stdoutLoggerHandler)
    return logger

def init_mail_logger(name=""):
    logger = logging.getLogger("LRM_{}_mail".format(name))
    mailLoggerHandler = myMailHandler(**config.mail_handler)
    mailLoggerHandler.setFormatter(FORMATTER)
    mailLoggerHandler.setLevel(logging.INFO)
    logger.addHandler(mailLoggerHandler)
    return logger


#mail handler
class myMailHandler(SMTPHandler):
    def emit(self, record):
        """
        Overwrite the logging.handlers.SMTPHandler.emit function with SMTP_SSL.
        Emit a record.
        Format the record and send it to the specified addressees.
        """
        try:
            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP_SSL(self.mailhost, port, timeout=self.timeout)
            msg = self.format(record)
            msg = "From: {}\r\nTo: {}\r\nSubject: {}\r\nDate: {}\r\n\r\n{}".format(self.fromaddr, ", ".join(self.toaddrs), self.getSubject(record), formatdate(), msg)
            if self.username:
                smtp.ehlo()
                smtp.login(self.username, self.password)
            smtp.sendmail(self.fromaddr, self.toaddrs, msg)
            smtp.quit()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)

AX_LOG_FORMAT="{timestamp}|{from_axle_sensor},\t\t{ax_number},\t\t{time_wheel_off},\t\t{time_wheel_on}\t\t{header};"
AX_LOG_FORMAT_P=": {timestamp}|{from_axle_sensor},\t\t{ax_number:d},\t\t{time_wheel_off:f},\t\t{time_wheel_on:f}\t\t{header};"
DATETIME_LOG_FORMAT= "%Y-%m-%d %H:%M:%S.%f"

def ax_sensor_log_gen(logger, axle_sensor_names):
    counter={n:0 for n in axle_sensor_names}
    while 1:
        axle_sensor_msg_frame, from_addr, timestamp, clear = yield None
        logger.debug("{}|{}|{}|{}".format(axle_sensor_msg_frame, from_addr, timestamp, clear))
        if clear:
            for n in axle_sensor_names:
                counter[n]=0
        from_axle_sensor_name = config.xbee_axle_sensors_name_from_addr(from_addr)
        logger.debug("{}".format(from_axle_sensor_name))
        counter[from_axle_sensor_name] += 1
        axle_sensor_msg_frame['from_axle_sensor'] = from_axle_sensor_name
        axle_sensor_msg_frame['ax_number'] = counter[from_axle_sensor_name]
        axle_sensor_msg_frame['timestamp'] = timestamp.strftime(DATETIME_LOG_FORMAT)
        if axle_sensor_msg_frame['header'] == 'MSG_HEADER_AXLE':
            logger.info(AX_LOG_FORMAT.format(**axle_sensor_msg_frame))
        elif axle_sensor_msg_frame['header'] == 'MSG_HEADER_ERROR':
            logger.warning(AX_LOG_FORMAT.format(**axle_sensor_msg_frame))
        else:
            logger.error(str(axle_sensor_msg_frame))

def _ax_sensor_log_row_parser(row):
    p = parse.search(AX_LOG_FORMAT_P, row)
    if p is not None:
        content = p.named
        content["timestamp"] = datetime.datetime.strptime(content['timestamp'],DATETIME_LOG_FORMAT)
        return  content
    else:
        return None

def ax_sensor_log_parser(filepath):
    ax = {"MSG_HEADER_AXLE": {},
          "MSG_HEADER_AXLE_ERROR": {}}
    with filepath.open("r+") as f:
        for row in f.readlines():
            content =_ax_sensor_log_row_parser(row)
            if content is not None:
                header=content.pop("header")
                timestamp=content.pop("timestamp")
                ax[header][timestamp] = content
    return ax

