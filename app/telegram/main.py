import logging
import asyncio
from asyncio.exceptions import CancelledError
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from faststream import FastStream

from app.db.database import r, create_tables, drop_tables, close_databases
from app.db.services.redis_db import RedisClient

from app.common.config import settings
from app.common.loggers import setup_logging
from app.telegram.handlers import setup_routers, setup_middlewares

from app.telegram.utils.infinity_parser import infinity_get_data_coins
from app.telegram.utils.handle_task import stop_task
from app.telegram.utils.start_fastream_broker import sub_faststream_tasks
from app.telegram.payments.freekassa import handle_payment_fk
from app.telegram.payments.paykassa import handle_payment_pk

import json
logger = logging.getLogger('system')


async def on_startup(dispatcher: Dispatcher, bot: Bot):
    setup_routers(dispatcher)
    setup_middlewares(dispatcher)
    setup_logging()
    logger.info("Starting telegram bot")
    await bot.delete_webhook(drop_pending_updates=True)

    if settings.BOT_MODE == 'webhook':
        await bot.set_webhook(f"{settings.WEBHOOK_URL}{settings.WEBHOOK_PATH}")

    try:
        await bot.send_message(chat_id=settings.DEV_ID, text="✅ <b>Bot started</b>")
    except:
        pass

async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()
    await close_databases()
    await bot.send_message(chat_id=settings.DEV_ID, text="🛑 <b>Bot stopped</b>")
    await bot.delete_my_commands()


async def create_bot_and_dispatcher() -> (Bot,Dispatcher):
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = RedisStorage(r)
    dp = Dispatcher(bot=bot, storage=storage)
    return bot, dp



async def run_webhook_mode(dp: Dispatcher, bot: Bot, faststream_app: FastStream, background_task):
    app = web.Application()
    app['bot'] = bot
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=settings.WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    faststream_task = asyncio.create_task(faststream_app.start()) if faststream_app else None

    app.router.add_post('/payment-pk', handle_payment_pk)
    #app.router.add_post('/payment-fk', handle_payment_fk)



    try:
        await web._run_app(app, host=settings.WEBHOOK_HOST, port=settings.WEBHOOK_PORT)
    except (KeyboardInterrupt, CancelledError):
        pass
    finally:
        if faststream_app:
            await faststream_app.stop()
            await stop_task(faststream_task, "faststream", timeout=2)
        await stop_task(background_task, "background")


async def run_polling_mode(dp: Dispatcher, bot: Bot, faststream_app: FastStream, background_task):
    faststream_task = asyncio.create_task(faststream_app.start()) if faststream_app else None

    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, CancelledError):
        pass
    finally:
        if faststream_app:
            await faststream_app.stop()
            await stop_task(faststream_task, "faststream", timeout=1)
        await stop_task(background_task, "background")





async def main():
    #TODO: Нужно добавить: 1. Запуск всех запущенных процессов.
    setup_logging()
    logger.info(f"Start {settings.PROJECT_NAME} (service: {settings.SERVICE_NAME})")
    if settings.DROP_TABLES:
        logger.info("Dropping tables")
        await drop_tables()
    await create_tables()

    bot, dp = await create_bot_and_dispatcher()
    await bot.delete_webhook(drop_pending_updates=True)

    broker, faststream_app = await sub_faststream_tasks(bot)


    background_task = asyncio.create_task(infinity_get_data_coins(r))

    if broker:
        dp.broker = broker

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    dp['broker']=broker

    redis_client=RedisClient(r)
    await redis_client.initialize()
    dp['redis_client']=redis_client

    if settings.BOT_MODE == 'webhook':
        logger.info("Starting bot in webhook mode")
        await run_webhook_mode(dp, bot, faststream_app, background_task)
    else:
        logger.info("Starting bot in polling mode")
        await run_polling_mode(dp, bot, faststream_app, background_task)


if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
