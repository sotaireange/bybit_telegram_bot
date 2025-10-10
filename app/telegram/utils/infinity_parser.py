import time
import logging
import asyncio
import pandas as pd
import ccxt.async_support as ccxt
from typing import Dict
import numpy as np
from ccxt import RequestTimeout
from aiogram.fsm.storage.redis import Redis

from app.db.services import RedisClient

from app.common.config import settings


logger=logging.getLogger('system')


async def get_all_instrument_info(exchange: ccxt) -> Dict:

    endpoint = 'v5/market/instruments-info'
    method = 'GET'
    params = {'category': 'linear','limit':1000}

    response = (await exchange.request(endpoint, method=method, params=params))
    df=pd.DataFrame(response['result']['list'])
    cols_to_keep=['qtyStep','minOrderQty','tickSize','symbol']
    df['qtyStep'] = np.array([float(x['qtyStep']) for x in df['lotSizeFilter']])
    df['minOrderQty'] = np.array([float(x['minOrderQty']) for x in df['lotSizeFilter']])
    df['tickSize'] = np.array([float(x['tickSize']) for x in df['priceFilter']])
    df=df.loc[:,cols_to_keep]

    df.set_index('symbol', inplace=True)
    mask = np.char.endswith(df.index.values.astype(str), 'USDT')
    df = df[mask]

    return df.to_dict(orient='index')

async def _get_tickers_for_auto_mode(exchange: ccxt, data_for_coins: Dict) -> pd.DataFrame:
    endpoint = '/v5/market/tickers'
    method = 'GET'
    params = {'category': 'linear'}

    response = (await exchange.request(endpoint, method=method, params=params))
    df = pd.DataFrame(response['result']['list'])

    cols_to_keep = ['markPrice', 'price24hPcnt', 'turnover24h', 'symbol']
    df = df.loc[:, cols_to_keep]
    df.set_index('symbol', inplace=True)
    mask = np.char.endswith(df.index.values.astype(str), 'USDT')
    df = df[mask]
    df = df.astype(float)
    df['price24hPcnt'] *= 100

    df['Long'] = ((df['price24hPcnt'] <= data_for_coins.get('long_percentage', -10)) &
                  (df['turnover24h'] > data_for_coins.get('volume_long', 30_000_000)))
    df['Short'] = ((df['price24hPcnt'] >= data_for_coins.get('short_percentage', 10)) &
                   (df['turnover24h'] > data_for_coins.get('volume_short', 30_000_000)))

    return df


async def _get_tickers_for_manual_mode(exchange: ccxt, data_for_coins: Dict) -> pd.DataFrame:
    endpoint = '/v5/market/tickers'
    params = {'category': 'linear'}
    method='GET'
    response = (await exchange.request(endpoint, method=method, params=params))
    df = pd.DataFrame(response['result']['list'])

    cols_to_keep = ['markPrice', 'turnover24h','price24hPcnt', 'symbol'] #
    df = df.loc[:, cols_to_keep]
    df.set_index('symbol', inplace=True)
    mask = np.char.endswith(df.index.values.astype(str), 'USDT')
    df = df[mask]
    df = df.astype(float)


    async def get_price_x_days_ago(symbol:str,days:int=3):
        ts_days_ago = int((time.time() - (24*days) * 3600) * 1000)

        ohlcv = await exchange.fetch_ohlcv(symbol, '1m', since=ts_days_ago-50000, limit=5)

        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')

        df['diff'] = abs(df['timestamp'] - ts_days_ago)
        nearest_candle = df.loc[df['diff'].idxmin()]
        return (nearest_candle['open']+nearest_candle['close'])/2


    tasks = {symbol: asyncio.create_task(get_price_x_days_ago(symbol)) for symbol in df.index}
    historical_prices = await asyncio.gather(*tasks.values())

    price_days_ago_series = pd.Series(dict(zip(tasks.keys(), historical_prices)), name='priceDaysAgo').dropna()
    df = df.join(price_days_ago_series)
    df.dropna(inplace=True)

    df['priceDaysAgoPcnt'] = ((df['markPrice'] - df['priceDaysAgo']) / df['priceDaysAgo']) * 100

    df['Long'] = ((df['priceDaysAgoPcnt'] >= data_for_coins.get('long_percentage', 150)) &
                  (df['turnover24h'] > data_for_coins.get('volume_long', 30_000_000)))
    df['Short'] = False

    return df


async def get_all_tickers(exchange: ccxt, data_for_coins: Dict) -> pd.DataFrame:
    strategy_map = {
        'auto': _get_tickers_for_auto_mode,
        'manually': _get_tickers_for_manual_mode,
    }

    selected_strategy = strategy_map.get(settings.TRADING_MODE)



    return await selected_strategy(exchange, data_for_coins)



async def infinity_get_data_coins(redis: Redis):
    logger.info('Start infinity get_data_coins')

    exchange = ccxt.bybit({
        'enableRateLimit': False,
    })
    redis_client=RedisClient(redis)

    last_info_update = 0

    logger.info('Infinity parser succes start')
    try:
        while True:
            try:
                now = time.time()

                if now - last_info_update > 3600:
                    data = await get_all_instrument_info(exchange)
                    await redis_client.save_coins_info(data)
                    last_info_update = now

                global_coin_settings=(await redis_client.get_all_coin_settings()).to_dict()
                df = await get_all_tickers(exchange,global_coin_settings)


                mark_prices=df['markPrice'].to_dict()
                await redis_client.save_mark_price_coins(mark_prices)

                drop_columns=['markPrice','price24hPcnt','turnover24h']
                df=df.drop(columns=drop_columns,axis=1)
                df=df[df.any(axis=1)]
                data=df.to_dict(orient='index')
                if data:

                    await redis_client.save_coins(data)


                await asyncio.sleep(1)

            except RequestTimeout as ReqEr:
                logger.exception(f"Request Timeout {ReqEr}")
                await exchange.close()
                await asyncio.sleep(10)
                exchange = ccxt.bybit({
                    'enableRateLimit': False,
                })


            except Exception as e:
                logger.exception(e)
                await exchange.close()
                await asyncio.sleep(60)
                exchange = ccxt.bybit({
                    'enableRateLimit': False,
                })


    except asyncio.CancelledError as e:
        logger.warning(f'Task cancel{e}')
    finally:
        await exchange.close()



if __name__ == '__main__':
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    from app.db.database import r

    from app.common.loggers import setup_logging
    setup_logging()
    logger=logging.getLogger('admin')

    asyncio.run(infinity_get_data_coins(r))