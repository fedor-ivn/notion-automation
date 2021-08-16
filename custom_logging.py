import logging
import coloredlogs

log_format = f"%(asctime)s - [%(levelname)s] - %(name)s - (%(filename)s).%(funcName)s(%(lineno)d) - %(message)s"


def get_logger(name, level=logging.DEBUG):
    # logging.basicConfig()
    logger = logging.getLogger(name)
    logger.setLevel(level)
    coloredlogs.install(level=level, logger=logger)
    return logger

