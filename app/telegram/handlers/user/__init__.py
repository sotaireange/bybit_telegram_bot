from aiogram import Router
navigate_router= Router(name='navigate')
setting_router=Router(name='setting')


from . import nav_handler
from . import set_handler