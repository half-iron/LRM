"""

add as crontab job

sudo crontab -e

*/5 * * * * /usr/bin/python3 /home/debian/measurement-system/auto_reboot_if_internet_fail.py 

log file in home folder "auto_reboot_if_internet_fail.log"  


"""
from subprocess import Popen
import time
import socket
import pathlib
import logging
import smtplib
import imaplib
import sys,os
from email.mime.text import MIMEText


mail_credentials = {
                    "smtp_server":'smtp.gmail.com',
                    "smtp_port":465,
                    "imap_server":"imap.gmail.com",
                    "imap_port":993,
                    "fromaddr":"rblraspberry@gmail.com",
                    "toaddrs":"enzo.scossa.romano@gmail.com",
                    "credentials":("rblraspberry@gmail.com","akustik16")
                       }

def send_mail(subject,msg,toaddrs,fromaddr,smtp_server,smtp_port,credentials,**kwargs):
    msg_ok = MIMEText(msg)
    msg_ok['Subject'] = subject
    msg_ok['From'] = fromaddr
    msg_ok['To'] = toaddrs
    #
    server = smtplib.SMTP_SSL(smtp_server,smtp_port)
    server.ehlo()
    server.login(*credentials)
    server.sendmail(fromaddr, toaddrs, msg_ok.as_string())
    server.quit()

def read_mail(fromaddr,imap_server,imap_port,credentials,**kwargs):
    server = imaplib.IMAP4_SSL(imap_server)
    server.login(*credentials)
    server.select('inbox')
    typ, data = server.search(None, 'ALL')
    try:
        for num in data[0].split():
            typ, msg_data = server.fetch(num, '(RFC822)')
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    email = email.message_from_bytes(response_part[1])
                    subject = email['subject']
                    print(subject)
                    print("##############")
                    for part in email.walk():
                        if part.get_content_type() == "text/plain":  # ignore attachments/html
                            body = part.get_payload(decode=True)
                            print(body)
            typ, response = server.store(num, '+FLAGS', r'(\Seen)')
    finally:
        try:
            server.close()
        except:
            pass
        server.logout()

HUAWEI_USB_PORT=3
HUAWEI_WAKEUP_TIME=90
def ykushUSB(port,power):
    cmd = "/usr/bin/ykushcmd -{} {}".format(power, port)
    ret= Popen(cmd, shell=True).wait()
    time.sleep(0.5)
    return ret


def reboot():
    try:
        r=os.system("/sbin/shutdown -r now")
    except Exception as e:
        logger.info(str(e))
    else:
        logger.info(r)

def restart_service(service):
    cmd = "/bin/systemctl restart {}".format(service)
    return Popen(cmd, shell=True).wait()

def test_internet_comnnection():
    hostname = "www.google.com"
    try:
        # see if we can resolve the host name -- tells us if there is
        # a DNS listening
        host = socket.gethostbyname(hostname)
        # connect to the host -- tells us if the host is actually
        # reachable
        s = socket.create_connection((host, 80), 5)
    except:
        return False
    else:
        return True


def unbind_bind_usb_root():
    cmd = "echo 'usb1' > /sys/bus/usb/drivers/usb/{}"
    Popen(cmd.format("unbind"), shell=True).wait()
    time.sleep(5)
    Popen(cmd.format("bind"), shell=True).wait()
    time.sleep(5)


if __name__=="__main__":
    formatter = logging.Formatter('%(asctime)s | %(name)s |  %(levelname)s: %(message)s')

    path =pathlib.Path("/home/debian/auto_reboot_if_internet_fail.log")

    logger = logging.getLogger("name")
    logger.setLevel('INFO')
    loggerHandler0 = logging.StreamHandler(sys.stdout)
    logger.addHandler(loggerHandler0)

    loggerHandler = logging.FileHandler(path.as_posix(),mode = 'a')
    loggerHandler.setFormatter(formatter)
    logger.addHandler(loggerHandler)
    ##
    INTERNET_OK = False

    if test_internet_comnnection():
        logger.info("Internet ok")
        INTERNET_OK=True
        send_mail('Lausanne Triage Messung', 'internet ok', **mail_credentials)
    else:
        logger.warning('Reset huawei device and restart services')
        #unbind_bind_usb_root()
        ykushUSB(HUAWEI_USB_PORT,'d')
        time.sleep(2)
        ykushUSB(HUAWEI_USB_PORT,'u')
        time.sleep(HUAWEI_WAKEUP_TIME)
        restart_service("networking")
        restart_service("ssh-tunnel")
        time.sleep(10)


        if test_internet_comnnection():
            logger.info("Internet ok after reset")
            send_mail('Lausanne Triage Messung', 'internet ok after reset', **mail_credentials)
            INTERNET_OK = True
        else:
            logger.critical("Reboot")
            reboot()

    if False:#INTERNET_OK:
        try:
            mails = read_mail()
        except:
            logger.warning("Unable to read mails")
            pass
        else:
            subjects=[]
            if "reboot" in subjects:
                logger.critical("Reboot")
                reboot()
            elif "restart.services":
                logger.warning("restart services")
                restart_service("networking")
                restart_service("ssh-tunnel")
