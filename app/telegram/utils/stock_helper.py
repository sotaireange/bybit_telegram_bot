import asyncio
from typing import Dict,List
import pandas as pd
import random

from app.db.models import User
from app.exchange.bybit_async import BybitRequester, get_all_position,get_api_permissions,close_order

testnet=False


async def close_all_order_user(user:User):
    client:BybitRequester =BybitRequester(user.api, user.secret, False)
    try:
        positions = await get_all_position(client)
        if positions:
            for position in positions:
                if position:
                    await close_order(client,position)
                await asyncio.sleep(random.random())
    finally:
        await client.close()
    return positions


async def get_user_positions(user:User) -> List[Dict]:
    positions=[]
    if user.api and user.secret:
        client:BybitRequester =BybitRequester(user.api, user.secret, testnet)
        try:
            positions= await get_all_position(client)
        finally:
            await client.close()
    return positions


async def check_permissions(user:User) -> Dict:
    flag=user.api and user.secret
    readonly=False
    has_permission=False
    parentUid=0
    result={}
    if flag:
        client:BybitRequester =BybitRequester(user.api, user.secret, testnet)
        result=await get_api_permissions(client)
        await client.close()
        if result:
            permissions=pd.Series(result['permissions'])
            readonly=result.get('readOnly',-1)==0
            has_permission=(permissions['ContractTrade']==['Order','Position'] and
                            permissions['Derivatives']==['DerivativesTrade'])
            parentUid=result.get('parentUid')

    return {'status': readonly and has_permission and flag,
          'readonly': readonly,
          'permissions': has_permission,
          'has_api_secret': flag,
          'parentUid': parentUid,
          'result':result}




