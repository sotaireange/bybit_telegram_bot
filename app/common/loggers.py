import logging
from rich.logging import RichHandler
from rich.console import Console
import logging.handlers as handlers
import os
from pathlib import Path

from .config import settings

import sys
if sys.platform == 'win32':
    LOG_DIR = Path('C:/Users/sallo/Desktop/FreeLance/Final Project(WebStorm)/bybit_users/logs').resolve()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
else:
    LOG_DIR = Path(settings.LOG_DIR)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

def get_file_handler(name: str):
    file_path = os.path.join(LOG_DIR, f"{name}.log")
    handler = handlers.TimedRotatingFileHandler(
        filename=file_path,
        when="D",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter(settings.FORMAT_FILE, datefmt=settings.TIME_FORMAT))
    return handler


def setup_fast_streamlogging(
        level: int = logging.WARNING,
):
    for logger_name in logging.root.manager.loggerDict:
        if logger_name.startswith('faststream'):
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
            logger.addHandler(get_file_handler("worker"))


    faststream_root = logging.getLogger('faststream')
    faststream_root.setLevel(level)

def setup_logging(rich:bool=True):
    level=logging.getLevelName(settings.LOG_LEVEL)

    console = Console(width=170, color_system="auto"
                      )

    rich_handler = RichHandler(
        console=console,
        rich_tracebacks=True,
        tracebacks_show_locals=False,
        show_time=True,
    )

    console_handler=logging.StreamHandler()
    handlers=rich_handler if rich else console_handler

    logging.basicConfig(
        level=logging.DEBUG,
        format=settings.FORMAT_CONSOLE_LOG,
        force=True,
        datefmt=settings.TIME_FORMAT,
        handlers=[handlers]

    )
    logger_ccxt=logging.getLogger('ccxt')
    logger_ccxt.setLevel(logging.ERROR)

    logger_trading = logging.getLogger("trading")
    logger_trading.setLevel(level)
    logger_trading.addHandler(get_file_handler("trading"))

    logger_aiogram = logging.getLogger("aiogram")
    logger_aiogram.setLevel(level)
    logger_aiogram.addHandler(get_file_handler("aiogram"))

    logger_telegram = logging.getLogger("telegram")
    logger_telegram.setLevel(level)
    logger_telegram.addHandler(get_file_handler("telegram"))

    logger_admin = logging.getLogger("admin")
    logger_admin.setLevel(level)
    logger_admin.addHandler(get_file_handler("admin"))

    logger_broker = logging.getLogger("broker")
    logger_broker.setLevel(level)
    logger_broker.addHandler(get_file_handler("broker"))

    logger_system = logging.getLogger("system")
    logger_system.setLevel(level)
    logger_system.addHandler(get_file_handler("system"))

    logger_worker = logging.getLogger('worker')
    logger_worker.setLevel(level)
    logger_worker.addHandler(get_file_handler("worker"))


    logger_payment = logging.getLogger('payment')
    logger_payment.setLevel(level)
    logger_payment.addHandler(get_file_handler("payment"))





