
import logging

import sys

import os

from datetime import datetime

from config import config





def get_logger(name: str) -> logging.Logger:

    logger = logging.getLogger(name)

    if not logger.handlers:

        logger.setLevel(getattr(logging, config.LOG_LEVEL, logging.INFO))



        console = logging.StreamHandler(sys.stdout)

        console.setLevel(logging.DEBUG)

        fmt = logging.Formatter(

            '%(asctime)s | %(name)-20s | %(levelname)-7s | %(message)s',

            datefmt='%Y-%m-%d %H:%M:%S'

        )

        console.setFormatter(fmt)

        logger.addHandler(console)



        os.makedirs("logs", exist_ok=True)

        fh = logging.FileHandler(f'logs/bot_{datetime.now().strftime("%Y%m%d")}.log')

        fh.setLevel(logging.DEBUG)

        fh.setFormatter(fmt)

        logger.addHandler(fh)



    return logger

