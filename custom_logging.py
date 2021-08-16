import logging
import os
import ssl
from logging.handlers import SMTPHandler

import coloredlogs
from dotenv import load_dotenv

log_format = f"%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"
logging.basicConfig(format=log_format)

load_dotenv()

LOGGING_EMAIL_HOST = os.environ['LOGGING_EMAIL_HOST']
LOGGING_EMAIL_FROM_ADDRESS = os.environ['LOGGING_EMAIL_FROM_ADDRESS']
LOGGING_EMAIL_TO_ADDRESS = os.environ['LOGGING_EMAIL_TO_ADDRESS']
LOGGING_EMAIL_USER = os.environ['LOGGING_EMAIL_USER']
LOGGING_EMAIL_PASSWORD = os.environ['LOGGING_EMAIL_PASSWORD']


def get_logger(name, level=logging.DEBUG):
    logger = logging.getLogger(name)
    logger.setLevel(level)

    smtp_handler = SMTPHandler(
        mailhost=LOGGING_EMAIL_HOST,
        fromaddr=LOGGING_EMAIL_FROM_ADDRESS,
        toaddrs=LOGGING_EMAIL_TO_ADDRESS,
        subject='An error occurred while running repeaters',
        credentials=(LOGGING_EMAIL_USER, LOGGING_EMAIL_PASSWORD),
        secure=(None, None, ssl.create_default_context())
    )
    smtp_handler.setLevel(logging.ERROR)
    logger.addHandler(smtp_handler)

    coloredlogs.install(level=level, logger=logger)

    return logger

