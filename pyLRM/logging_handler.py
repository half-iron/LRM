from logging.handlers import SMTPHandler
import logging
import importlib
import smtplib
from email.utils import formatdate
import sys

config = importlib.import_module('config')
formatter = logging.Formatter('%(asctime)s | %(name)s |  %(levelname)s: %(message)s')



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



def init_logger(name,filepath):
    logger = logging.getLogger(name)
    logger.setLevel('DEBUG')
    loggerPath = filepath.joinpath('messsystem.log')
    loggerHandler = logging.FileHandler(loggerPath.as_posix())
    loggerHandler.setFormatter(formatter)
    # add filehandler
    logger.addHandler(loggerHandler)
    # add standardout handler
    loggerHandler2 = logging.StreamHandler(sys.stdout)
    logger.addHandler(loggerHandler2)
    # add mail handler
    mail_handler = myMailHandler(**config.mail_handler)
    # mail_handler.setFormatter(formatter)
    mail_handler.setLevel(logging.CRITICAL)
    logger.addHandler(mail_handler)

    # AxleSensor data logger
    DataLogger = logging.getLogger("axle_data")
    DataLogger.setLevel('INFO')
    DataLogPath = filepath.joinpath('axle_data.log')
    DataLogHandler = logging.FileHandler(DataLogPath.as_posix())
    DataLogger.addHandler(DataLogHandler)

    return logger,DataLogger

if __name__=="__main__":
    import pathlib
    # test spedire una mail
    path = pathlib.Path().joinpath('test')
    logger,_=init_logger('aa',path)
    logger.info('Setup completato')
    logger.critical("ERRORE CRITICO")
