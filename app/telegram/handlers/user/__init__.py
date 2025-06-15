from aiogram import Router
navigate_router= Router(name='navigate')
setting_router=Router(name='setting')

from .run import router as run_router
from . import nav_handler
from . import set_handler