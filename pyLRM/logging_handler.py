from logging.handlers import SMTPHandler
import logging
import smtplib
from email.utils import formatdate
import sys
import pathlib
import pyLRM.config as config


FORMATTER = logging.Formatter('%(asctime)s | %(name)s |  %(levelname)s: %(message)s')

def init_logger(name="", level = "INFO", filepath=pathlib.Path(), systdout=True, file=True, mail=False):

    LRMsysLogger= logging.getLogger("LRM_{}".format(name))
    LRMsysLogger.setLevel(level)

    if file:
        # add file handler
        messystemFilePath = filepath.joinpath("LRM_{}.log".format(name))
        messystemFileLoggerHandler = logging.FileHandler(messystemFilePath.as_posix())
        messystemFileLoggerHandler.setFormatter(FORMATTER)
        # add file handler
        LRMsysLogger.addHandler(messystemFileLoggerHandler)

    if systdout:
        #standardout handler
        stdoutLoggerHandler = logging.StreamHandler(sys.stdout)
        stdoutLoggerHandler.setFormatter(FORMATTER)
        LRMsysLogger.addHandler(stdoutLoggerHandler)


    if mail:
        # add mail handler
        mailLoggerHandler = myMailHandler(**config.mail_handler)
        # mail_handler.setFormatter(formatter)
        mailLoggerHandler.setLevel(logging.CRITICAL)
        LRMsysLogger.addHandler(mailLoggerHandler)

    return LRMsysLogger


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