import asyncio
from typing import Dict,List
import pandas as pd
import random
from app.common.config import settings
from app.db.models import User
from app.exchange.bybit_async import BybitRequester, get_all_position,get_api_permissions,close_order
from app.db.services import postgres_db as pdb
from sqlalchemy.ext.asyncio import AsyncSession



testnet=False


async def close_all_order_user(user:User,api_name:str=None):
    apis = user.get_api(api_name)
    client:BybitRequester =BybitRequester(apis.api, apis.secret, False)
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


async def get_user_positions(user:User,api_name:str=None) -> List[Dict]:
    positions=[]
    apis=user.pick_api(api_name)
    if apis:
        client:BybitRequester =BybitRequester(apis.api, apis.secret, testnet)
        try:
            positions= await get_all_position(client)
        finally:
            await client.close()
    return positions

async def get_unrealised_pnl_user(user:User) -> float:
    pstns=await get_user_positions(user)
    sum_pnl=0
    if pstns:
        df=pd.DataFrame(pstns)
        sum_pnl=round((df['unrealisedPnl'].astype(float)).sum(),2)
    return sum_pnl


async def check_permissions(user:User,api_name:str=None) -> Dict:
    apis=user.pick_api(api_name)
    readonly=False
    has_permission=False
    parentUid=0
    userID=0
    ret_code=0
    ret_msg=None
    result={}
    if apis:
        client:BybitRequester =BybitRequester(apis.api, apis.secret, testnet)
        try:
            result=await get_api_permissions(client)
        finally:
            await client.close()
        ret_code=result.get('retCode',0)
        ret_msg=result.get('retMsg',None)
        if result and ret_code==0:
            permissions=pd.Series(result['permissions'])
            readonly=result.get('readOnly',-1)==0
            has_permission=(permissions['ContractTrade']==['Order','Position'] and
                            permissions['Derivatives']==['DerivativesTrade'])
            parentUid=result.get('parentUid')
            userID=result.get('userID',0)

    return {'status': readonly and has_permission and apis,
          'readonly': readonly,
          'permissions': has_permission,
          'has_api_secret': apis is not None,
          'parentUid': parentUid,
          'result':result,
          'ret_code':ret_code,
          'ret_msg':ret_msg,
          'userID': userID}



async def check_bybit_uids(db:AsyncSession,user:User,data:dict):
    if settings.TRADING_MODE=='manually':
        return True
    bybit_uid=int(data.get('parentUid',0))
    bybit_sub_account_uid=int(data.get('userID',0))
    if bybit_uid:
        await pdb.update_bybit_uid(db,user.id,bybit_uid)
    if bybit_sub_account_uid:
        await pdb.update_bybit_subaccount_uid(db,user.id,bybit_sub_account_uid)