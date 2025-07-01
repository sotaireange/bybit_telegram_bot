import asyncio
import pandas as pd
from itertools import chain

from datetime import datetime

from typing import Dict, List,Union,Sequence

from app.db.models import User
from app.exchange.bybit_async import BybitRequester, get_pnl_from_chunks
from app.telegram.utils.datetime_helper import TimeSplitter
from app.telegram.utils.stock_helper import testnet




async def get_pnl_result_from_chunk(bybit_requester:BybitRequester, chunks:List[Dict[str,datetime]]) -> List[Dict]:
    tasks=[]
    for chunk in chunks:
        tasks.append(get_pnl_from_chunks(bybit_requester,chunk))
    tasks_result=await asyncio.gather(*tasks)
    result=[item for sublist in tasks_result for item in sublist]
    return result


async def get_user_pnl(user: User, use_last_sub_day:bool=False,only_sum=False) -> Union[pd.DataFrame,float]:
    df=pd.DataFrame()
    client=None
    if not (user.api and user.secret): return df if not only_sum else 0
    try:
        client=BybitRequester(user.api, user.secret, testnet)
        splitter = TimeSplitter(user)

        chunk_weeks = splitter.get_recent_weeks(months_back=3,use_last_sub_day=use_last_sub_day)
        tasks=[get_pnl_result_from_chunk(client, chunk) for chunk in chunk_weeks]
        results=await asyncio.gather(*tasks)

        df=pd.DataFrame(list(chain.from_iterable(results)))
        needed_cols=['updatedTime','closedPnl','createdTime']
        df = df[needed_cols].copy()
        df['updatedTime'] = pd.to_datetime(df['updatedTime'].astype('float64'), unit='ms')
        df['createdTime'] = pd.to_datetime(df['createdTime'].astype('float64'), unit='ms')
        df['closedPnl'] = df['closedPnl'].astype(float)

    finally:
        if client:
            await client.close()
        return df if not only_sum else df['closedPnl'].sum() if len(df)>0 else 0


async def get_all_user_pnl(users: Sequence[User]) -> Dict[User,float]:
    tasks=[(get_user_pnl(user,True,only_sum=True)) for user in users]
    results=await asyncio.gather(*tasks)
    # pnl_users={user.id:results[i] for i,user in enumerate(users)}
    pnl_users=dict(zip(users,results))
    return pnl_users