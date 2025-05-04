import logging
import sys
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage


from app.common.config import settings
from app.common import loggers

from app.telegram.handlers import setup_routers
from app.telegram.handlers import setup_middlewares


from app.db.database import r,AsyncSessionLocal,create_tables,drop_tables



async def main():
    try:
        bot = Bot(token=settings.BOT_TOKEN,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
        storage = RedisStorage(r)
        #await drop_tables()
        await create_tables()
        dp = Dispatcher(storage=storage)
        setup_routers(dp)
        setup_middlewares(dp)
        await dp.start_polling(bot)
    except Exception as e:
        logging.exception(f"ERROR MAIN \n\n\nALARM\n\n\n {e}")


if __name__ == "__main__":
    asyncio.run(main())