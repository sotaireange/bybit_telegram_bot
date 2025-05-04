import time
import logging
import asyncio


import ccxt.async_support as ccxt
from aiogram.fsm.storage.redis import Redis

from app.db.services import RedisClient

from .utils import get_instrument_info,get_all_tickers



logger=logging.getLogger('admin')


async def infinity_get_data_coins(redis: Redis):
    exchange = ccxt.bybit({
        'enableRateLimit': False,
    })
    redis_client=RedisClient(redis)

    last_info_update = 0


    try:
        while True:
            try:
                now = time.time()

                # Обновление instrument_info раз в час
                if now - last_info_update > 3600:
                    data = await get_instrument_info(exchange)
                    await redis_client.save_coins_info(data)
                    last_info_update = now

                global_coin_settings=(await redis_client.get_all_trade_settings()).to_dict()
                df = await get_all_tickers(exchange,global_coin_settings)


                mark_prices=df['markPrice'].to_dict()
                await redis_client.save_mark_price_coins(mark_prices)

                drop_columns=['markPrice','price24hPcnt','turnover24h']
                df=df.drop(columns=drop_columns,axis=1)
                df=df[df.any(axis=1)]
                data=df.to_dict(orient='index')
                await redis_client.save_coins(data)


                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(e)
                await exchange.close()
                await asyncio.sleep(1200)
                exchange = ccxt.bybit({
                    'enableRateLimit': False,
                })
    finally:
        await exchange.close()
