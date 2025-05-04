import logging
from rich.logging import RichHandler
from rich.console import Console
import logging.handlers as handlers
import os

from .config import settings
FORMAT_CONSOLE = "%(name)s|%(funcName)s(%(lineno)d)| | %(message)s"
FORMAT_FILE="%(asctime)s %(levelname)s %(name)s [%(module)s.%(funcName)s(%(lineno)d)] | %(message)s"
TIME_FORMAT= '[%X %d-%m-%Y]'

console = Console(width=170, color_system="auto"
                  )

rich_handler = RichHandler(
    console=console,
    rich_tracebacks=True,
    tracebacks_show_locals=False,
    show_time=True,
)

console_handler=logging.StreamHandler()



logging.basicConfig(
    level=logging.DEBUG,
    format=FORMAT_CONSOLE,
    force=True,
    datefmt=TIME_FORMAT,
    handlers=[#console_handler,
              rich_handler
              ]
)



logger1 = logging.getLogger("trading")
file_handler = handlers.TimedRotatingFileHandler(f"{logger1.name}.log",when="D", interval=1, backupCount=7)
file_handler.setFormatter(logging.Formatter(FORMAT_FILE,
                                            datefmt=TIME_FORMAT
                                            ))
logger1.addHandler(file_handler)


logger_aiogram=logging.getLogger("aiogram")
file_handler = handlers.TimedRotatingFileHandler(f"{logger_aiogram.name}.log",when="D", interval=1, backupCount=7)
file_handler.setFormatter(logging.Formatter(FORMAT_FILE,
                                            datefmt=TIME_FORMAT
                                            ))

logger_aiogram.addHandler(file_handler)


logger_telegram = logging.getLogger('telegram')
logger_telegram.addHandler(file_handler)

logger_admin = logging.getLogger('admin')
file_handler_admin = handlers.TimedRotatingFileHandler(f"{logger_admin.name}.log",when="D", interval=1, backupCount=7)
file_handler_admin.setFormatter(logging.Formatter(FORMAT_FILE,
                                            datefmt=TIME_FORMAT
                                            ))
logger_admin.addHandler(file_handler_admin)