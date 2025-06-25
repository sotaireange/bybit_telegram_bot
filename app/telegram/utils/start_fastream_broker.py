import logging
from typing import Tuple, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from aiogram import Bot
from faststream import FastStream
from faststream.log import logger
from faststream.redis import RedisBroker


from app.common.config import settings
from app.common.loggers import setup_fast_streamlogging
from app.telegram.utils.notifications import send_notification
from app.worker.broker import create_redis_broker, subscribe_to_telegram_messages

logger.setLevel(logging.WARNING)


async def sub_faststream_tasks(bot: Bot) -> Tuple[Optional[RedisBroker], Optional[FastStream]]:

    broker: Optional[RedisBroker] = None
    faststream_app: Optional[FastStream] = None

    if settings.USE_BROKER:
        broker = await create_redis_broker(settings.REDIS_URL)
        subscribe_to_telegram_messages(broker, lambda msg: send_notification(bot, msg))
        faststream_app = FastStream(broker=broker,
                                    logger=logger)
        logger.info('FastStream in Telegram successfully started')
        setup_fast_streamlogging(logging.WARNING)
    else:
        logger.info('FastStream disabled by settings')
        
    return broker, faststream_app

