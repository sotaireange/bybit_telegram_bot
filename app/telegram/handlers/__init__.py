from aiogram import Dispatcher

from app.db.database import (r,
                         AsyncSessionLocal as db)

from .admin import router as admin_router, router_setting as admin_setting_router
from .pay import router as pay_router
from .user import navigate_router as nav_router
from .user import setting_router as set_router
from .user import run_router

from app.common.config import settings


from app.telegram.middlewares import (DatabaseMiddleware,
                                      RedisMiddleware,
                                      SetValueMiddleware,
                                      GetUsersMiddleware,
                                      AdminSetValueMiddleware,
                                      PaymentAmountMiddleware,
                                      ManuallyMiddleware)


def setup_routers(dp: Dispatcher):
    dp.include_routers(pay_router,run_router,admin_router,admin_setting_router,nav_router,set_router)


def setup_middlewares(dp: Dispatcher):
    #dp.update.middleware.register(RedisMiddleware(r))
    dp.update.middleware.register(DatabaseMiddleware(db))
    if settings.TRADING_MODE=='manually':
        dp.update.middleware.register(ManuallyMiddleware())
    set_router.message.middleware.register(SetValueMiddleware(db))

    nav_router.callback_query.middleware.register(GetUsersMiddleware(db))
    nav_router.message.middleware.register(GetUsersMiddleware(db))

    pay_router.callback_query.middleware.register(GetUsersMiddleware(db))
    pay_router.callback_query.middleware.register(PaymentAmountMiddleware(db))

    admin_router.callback_query.middleware.register(DatabaseMiddleware(db))
    admin_router.message.middleware.register(DatabaseMiddleware(db))
    admin_setting_router.message.middleware.register(AdminSetValueMiddleware(r))

    #run_router.callback_query.middleware.register(RedisMiddleware(r))
    run_router.callback_query.middleware.register(GetUsersMiddleware(db))
    run_router.callback_query.middleware.register(DatabaseMiddleware(db))


