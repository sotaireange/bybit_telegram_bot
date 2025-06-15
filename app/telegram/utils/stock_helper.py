import asyncio
from typing import Dict,List
import pandas as pd
import random

from app.db.models import User
from app.exchange.bybit_async import BybitRequester, get_all_position,get_api_permissions,close_order

testnet=False


async def close_all_order_user(user:User): #TODO Проблема с тем, то что не все позиции закрываются. НУжно сделать двойное-тройное закрытие
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
    # TODO: ВАЖНО!!! ПРОВЕРИТЬ ТО ,ЧТО API И SECRET ВАЛИДНЫЙ (RET_CODE=2025-06-10T16:52:59.477886427Z                                send_signed_request() returned exception: "Bybit API Error - retCode: 10003, retMsg: API key is invalid
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




