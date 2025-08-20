import asyncio
import logging
from typing import Callable,Optional
from aiohttp.client_exceptions import ClientConnectorDNSError
from faststream.redis import RedisBroker

from app.db.database import r,AsyncSessionLocal
from app.db.services import RedisClient, postgres_db as pdb
from app.db.models import Run,UserAPI
from app.common.config import settings
from app.exchange.user_trade.user_trade import TradeBot
from app.worker.broker import publish_telegram_message
from app.db.models import TelegramMessage,NotificationType


logger = logging.getLogger('trading')


async def trading_one_api_key(redis_client:RedisClient,user_id:int,api: UserAPI):
    if api.run:
        bot=TradeBot(user_id,api,redis_client)
        await bot.initialize()
        try:
            while bot.is_running!=Run.OFF:
                try:
                    logger.debug('Start Trade')
                    await bot.start_trade()
                    break
                except ClientConnectorDNSError as e:
                    await redis_client.set_is_run(user_id,Run.OFF)
                    bot.is_running=Run.OFF
                    logger.exception(f'Connection error: {e}, retrying in 10 minutes...\n'
                                     f'user_id={user_id}')
                    tg_msg=TelegramMessage(user_id=user_id,type=NotificationType.ERROR,data=None)
                    await publish_telegram_message(broker=bot.broker,telegram_message=tg_msg)
        finally:
            await bot.exit()
    return

async def trading(user_id: int):
    redis_client = RedisClient(r)
    # await redis_client.set_is_run(user_id, Run.ACTIVE)

    async with AsyncSessionLocal() as session:
        user = await pdb.get_user(session, user_id)

    apis = user.apis
    tasks = [asyncio.create_task(trading_one_api_key(redis_client, user_id, api)) for api in apis]

    try:
        while (await redis_client.get_is_run(user_id)) != Run.OFF:
            if all(task.done() for task in tasks):
                break
            await asyncio.sleep(1)

        for task in tasks:
            if not task.done():
                task.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

    except Exception as e:
        logger.exception(f"Error in trading for user {user_id}: {e}")
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__=="__main__":
    from app.common.loggers import setup_logging
    setup_logging()
    asyncio.run(trading(6422309975))