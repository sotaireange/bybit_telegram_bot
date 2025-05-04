from aiogram import Router

router= Router(name='admin')
router_setting=Router(name='admin_setting')

from . import admin_handler
from . import admin_setting_handler
from . import admin_commands