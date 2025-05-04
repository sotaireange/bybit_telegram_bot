import asyncio
from datetime import datetime
from typing import Dict,List
import pandas as pd
import random

from app.db.models import User
from app.exchange.bybit_async import BybitRequester,get_pnl_from_chunks,get_all_position,get_api_permissions,close_order
from app.telegram.utils.datetime_helper import get_month_bounds,split_into_weeks,filter_months

testnet=True


async def close_all_order_user(user:User):
    client:BybitRequester =BybitRequester(user.api, user.secret, True)
    positions = await get_all_position(client)
    for position in positions:
        await close_order(client,position)
        await asyncio.sleep(random.random())
    return positions


async def get_user_positions(user:User) -> List[Dict]:
    positions=[]
    if user.api and user.secret:
        client:BybitRequester =BybitRequester(user.api, user.secret, testnet)
        positions= await get_all_position(client)
    return positions



async def get_pnl_result(bybit_requester:BybitRequester, chunks:List[Dict[str,datetime]]) -> List[Dict]:
    tasks=[]
    for chunk in chunks:
        tasks.append(get_pnl_from_chunks(bybit_requester,chunk))
    tasks_result=await asyncio.gather(*tasks)
    result=[item for sublist in tasks_result for item in sublist]
    return result


async def check_permissions(user:User) -> Dict:
    flag=user.api and user.secret
    readonly=False
    has_permission=False
    result={}
    if flag:
        client:BybitRequester =BybitRequester(user.api, user.secret, testnet)
        result=await get_api_permissions(client)
        permissions=pd.Series(result['permissions'])
        readonly=result['readOnly']==0
        has_permission=(permissions['ContractTrade']==['Order','Position'] and
                        permissions['Options']==['OptionsTrade'] and
                        permissions['Derivatives']==['DerivativesTrade'])


    return {'status': readonly and has_permission and flag,
          'readonly': readonly,
          'permissions': has_permission,
          'has_api_secret': flag,
          'result':result}




async def get_three_month_pnl(user: User) -> Dict[datetime,float]:
    if not (user.api and user.secret): return {}
    client:BybitRequester =BybitRequester(user.api, user.secret, testnet)
    first_day_user=user.first_day
    months=[get_month_bounds(i,first_day_user) for i in range(3)]
    months=filter_months(first_day_user,months)
    chunks=[split_into_weeks(month) for month in months]
    tasks=[get_pnl_result(client,chunk) for chunk in chunks]
    results=await asyncio.gather(*tasks)
    total_pnls = {}

    for chunk, result in zip(chunks, results):
        if not result:
            continue
        # Предположим, что chunk — список словарей с ключом 'startTime'
        # Возьмём первую дату как начало интервала
        start_time = chunk[0]['startTime'] if chunk and 'startTime' in chunk[0] else None
        if start_time is None:
            continue
        pnl_sum = sum(float(item['closedPnl']) for item in result if 'closedPnl' in item)
        total_pnls[start_time] = pnl_sum

    return total_pnls
