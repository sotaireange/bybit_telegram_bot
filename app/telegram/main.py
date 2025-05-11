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


from app.common.config import settings
from app.common.loggers import setup_logging

from app.telegram.handlers import setup_routers
from app.telegram.handlers import setup_middlewares
from app.telegram.utils.notifications import send_notification

from app.db.database import r,create_tables,drop_tables,close_databases


from app.worker.broker import create_redis_broker,subscribe_to_telegram_messages
logger=logging.getLogger('system')





async def on_startup(dispatcher: Dispatcher, bot: Bot):
    setup_routers(dispatcher)
    setup_middlewares(dispatcher)
    setup_logging()
    logger.info("Starting telegram bot")
    await bot.delete_webhook(drop_pending_updates=True)
    if settings.BOT_MODE=='webhook':
        await bot.set_webhook(f"{settings.WEBHOOK_URL}{settings.WEBHOOK_PATH}")

    await bot.send_message(chat_id=settings.DEV_ID, text="✅ <b>Bot started</b>")


async def on_shutdown(dispatcher: Dispatcher, bot: Bot) -> None:
    #await broker.stop()
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()
    await close_databases()
    await bot.send_message(chat_id=settings.DEV_ID, text="🛑 <b>Bot stopped</b>")


async def main():
    logger.info(f"Start {settings.PROJECT_NAME} (sevice: {settings.SERVICE_NAME})")
    bot = Bot(token=settings.BOT_TOKEN,default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = RedisStorage(r)

    dp = Dispatcher(bot=bot,storage=storage)



    broker = None
    faststream_app = None
    faststream_task=None

    if settings.DROP_TABLES:
        await drop_tables()
    await create_tables()

    if settings.USE_BROKER:
        broker=await create_redis_broker(settings.REDIS_URL)
        subscribe_to_telegram_messages(broker, lambda msg: send_notification(bot, msg))
        faststream_app = FastStream(broker=broker)

        dp.broker = broker


    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)


    if settings.BOT_MODE == 'webhook':
        logger.info("Starting bot in webhook mode")
        app = web.Application()
        webhook_handler = SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
        )
        webhook_handler.register(app, path=settings.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        if faststream_app:
            faststream_task = asyncio.create_task(faststream_app.start())

        try:
            await web._run_app(
                app,
                host=settings.WEBHOOK_HOST,
                port=settings.WEBHOOK_PORT
            )
        except (KeyboardInterrupt,CancelledError):
            pass
        finally:
            if faststream_app:
                await faststream_app.stop()
                await asyncio.wait_for(faststream_task,timeout=1)
    else:
        logger.info("Starting bot in polling mode")
        if faststream_app:
            faststream_task = asyncio.create_task(faststream_app.start())

        try:
            await dp.start_polling(bot)

        except (KeyboardInterrupt,CancelledError):
            pass
        finally:
            # Останавливаем FastStream при выходе
            if faststream_app:
                await faststream_app.stop()
                await asyncio.wait_for(faststream_task,timeout=1)





if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())