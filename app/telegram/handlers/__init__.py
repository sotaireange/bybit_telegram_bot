import os

from aiogram import Dispatcher
from sqlalchemy.ext.asyncio import async_sessionmaker


from db.database import (r,
                         AsyncSessionLocal as db)

from .admin import router as admin_router, router_setting as admin_setting_router
from .pay import router as pay_router
from .user import navigate_router as nav_router
from .user import setting_router as set_router
from .run import router as run_router


#admins=os.getenv('ADMINS',[6422309975,])

from app.telegram.middlewares import (DatabaseMiddleware,
                                  RedisMiddleware,
                                  SetValueMiddleware,
                                  GetUsereMiddleware,
                                  AdminSetValueMiddleware)
from app.telegram.filter import Admin

def setup_routers(dp: Dispatcher):
    dp.include_routers(run_router,admin_router,admin_setting_router,pay_router,nav_router,set_router)



def setup_middlewares(dp: Dispatcher,):
    dp.update.middleware.register(RedisMiddleware(r))
    dp.update.middleware.register(DatabaseMiddleware(db))
    set_router.message.middleware.register(SetValueMiddleware(db))
    nav_router.callback_query.middleware.register(GetUsereMiddleware(db))
    nav_router.message.middleware.register(GetUsereMiddleware(db))

    admin_router.callback_query.middleware.register(DatabaseMiddleware(db))
    admin_router.message.middleware.register(DatabaseMiddleware(db))
    admin_setting_router.message.middleware.register(AdminSetValueMiddleware(r))
