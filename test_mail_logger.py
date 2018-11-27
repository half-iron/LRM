from pyLRM.logging_handler import init_logger
if __name__=="__main__":
    logger = init_logger('test_mail_logger',file=False,mail=True)
    logger.critical("This is a Test msg generated from test_mail_logger.py.")