import asyncio
import logging
from typing import Callable,Optional
from aiohttp.client_exceptions import ClientConnectorDNSError
from faststream.redis import RedisBroker

from app.db.database import r,AsyncSessionLocal
from app.db.services import RedisClient, postgres_db as pdb
from app.db.models import Run
from app.common.config import settings
from app.exchange.user_trade.user_trade import TradeBot



logger = logging.getLogger('trading')

async def trading(user_id:int):
    redis_client=RedisClient(r)
    # await redis_client.set_is_run(user_id,Run.ACTIVE)
    async with AsyncSessionLocal() as session:
        user= await pdb.get_user(session,user_id)
    data={'api_key':user.api,'api_secret':user.secret}
    bot=TradeBot(user_id,data,redis_client)
    await bot.initialize()
    try:
        while bot.is_running!=Run.OFF:
            try:
                logger.debug('Start Trade')
                await bot.start_trade()
                break
            except ClientConnectorDNSError as e: #TODO: Будущая возможная ошибка. Нужно сразу завершить и отправить сообщение об ошибке
                await redis_client.set_is_run(user_id,Run.OFF)
                bot.is_running=Run.OFF
                logger.error(f'Connection error: {e}, retrying in 10 minutes...\n'
                             f'user_id={user_id}')
                # await asyncio.sleep(100)
                # await redis_client.set_is_run(user_id,Run.ACTIVE)
                # bot.is_running=Run.ACTIVE
    finally:
        await bot.exit()



if __name__=="__main__":
    from app.common.loggers import setup_logging
    setup_logging()
    asyncio.run(trading(6422309975))