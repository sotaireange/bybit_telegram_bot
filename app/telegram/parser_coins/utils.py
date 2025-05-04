import pandas as pd
import ccxt.async_support as ccxt
from typing import Dict
import numpy as np

async def get_instrument_info(exchange: ccxt) -> Dict:

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


async def get_all_tickers(exchange: ccxt,data_for_coins: Dict) -> pd.DataFrame:

    endpoint = '/v5/market/tickers'
    method = 'GET'
    params = {'category': 'linear'}

    response = (await exchange.request(endpoint, method=method, params=params))
    df=pd.DataFrame(response['result']['list'])
    cols_to_keep = ['markPrice','price24hPcnt','turnover24h','symbol']
    df=df.loc[:,cols_to_keep]
    df.set_index('symbol', inplace=True)
    mask = np.char.endswith(df.index.values.astype(str), 'USDT')
    df = df[mask]
    df= df.astype(float)
    df['price24hPcnt']*=100

    df['Long']=((df['price24hPcnt']>=data_for_coins.get('long_percentage',10))& (df['turnover24h']>data_for_coins.get('volume_long',30_000_000)))
    df['Short']=((df['price24hPcnt']<=data_for_coins.get('short_percentage',-10))& (df['turnover24h']>data_for_coins.get('volume_short',30_000_000)))


    return df


