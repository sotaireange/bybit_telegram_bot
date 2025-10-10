import logging
import asyncio
from typing import Dict,Optional, Hashable, List,Union
from faststream.redis import RedisBroker

import numpy as np
import pandas as pd


from .strategies import TradingStrategy,get_trading_strategy

from app.common.config import settings

from app.db.services import RedisClient
from app.db.models import (Run,TradeSettings,MainPosition,
                           SecondaryPosition,TelegramMessage,
                           NotificationType,UserAPI)


from app.exchange.bybit_async import BybitRequester
from app.exchange.bybit_async import (get_positions,get_order,
                                      get_mark_price,set_leverage,
                                      get_balance,get_all_position,
                                      place_order,switch_position_mode,
                                      change_tp_price,close_order)

from app.exchange.user_trade.utils import (improved_round_step_size,round_step_size, proof_result)
from app.exchange.user_trade.orders import HedgePositionManager,PositionIdx

logger=logging.getLogger('trading')



from app.worker.broker import publish_telegram_message


import sys
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class TradeBot:
    def __init__(self,user_id:int,api:UserAPI,redis_client:RedisClient):
        self.is_running: Run= Run.ACTIVE

        self.user_id = user_id
        self.client: Optional[BybitRequester] = None
        self.api=api

        self.settings: TradeSettings= TradeSettings()

        self.redis=redis_client.redis
        self.redis_client=redis_client
        self.hp_manager:HedgePositionManager

        self.is_notification=True
        self.all_task=[]
        self.send_notification=publish_telegram_message
        self.broker=RedisBroker(settings.REDIS_URL)
        self.strategy = get_trading_strategy(
            mode=settings.TRADING_MODE,
            context=self
        )

    async def init_broker(self):
        await self.broker.start()

    def set_client(self,testnet:Optional[bool]=None):
        if self.client is not None:
            try:
                self.client.close()
            except:
                pass
        if testnet is None:
            testnet=settings.TESTNET
        self.client:BybitRequester=BybitRequester(self.api.api,self.api.secret,testnet=testnet)


    async def update_settings(self):
        self.settings.update((await self.redis_client.get_all_trade_settings()).to_dict())


    async def init_hp_manager(self):
        self.hp_manager=HedgePositionManager(self.user_id,self.redis,self.settings,self.api.name)
        await self.hp_manager.load_from_redis()


    async def initialize(self):
        self.set_client(testnet=False)
        await self.update_settings()
        await self.init_hp_manager()
        await self.init_broker()


    async def exit(self):
        await self.client.close()
        await self.broker.close()


    async def prepare_and_notification(self,position_object:Union[MainPosition,SecondaryPosition],open:bool):
        if position_object and self.is_notification:
            msg = TelegramMessage(user_id=self.user_id, type=NotificationType.POSITION_OPEN if open else NotificationType.POSITION_CLOSE
                                  , data=position_object)
            await self.send_notification(self.broker, msg)


    async def check_settings(self):
        while self.is_running!=Run.OFF:
            await self.update_settings()
            await asyncio.sleep(1)


    async def check_running(self):
        while True:
            self.is_running=await self.redis_client.get_is_run(self.user_id)
            await asyncio.sleep(0.5)
            if self.is_running==Run.OFF:
                break


    async def should_close(self):
        balance=await get_balance(self.client)
        if proof_result(balance,dict):
            available_balance=float(balance.get('totalAvailableBalance',0))
            total_balance=float(balance.get('totalWalletBalance',1))
            return ((available_balance/(total_balance+0.000000001)<0.1) and total_balance>70)
        return False


    async def have_balance(self):
        balance=await get_balance(self.client)
        if proof_result(balance,dict):
            available_balance=float(balance.get('totalAvailableBalance',0))
            total_balance=float(balance.get('totalWalletBalance',1))
            return ((available_balance+0.00000001/(total_balance+0.00001) > (1-self.settings.balance/100)) and (available_balance>5.0))
        logger.warning('Balance in have_balance does not dict')
        return False


    async def have_both_side_position(self,coin: Hashable) -> bool:
        positions=await get_positions(self.client,coin)
        if proof_result(positions,list):
            len_p=len(positions)
            size=[float(position.get('size',0)) for position in positions]
            return (len_p==2 and all(size))
        logger.warning('Position  does not list')
        return True


    async def coin_in_trade(self, coin: Hashable) -> bool:
        position=(await get_positions(self.client,coin))
        if proof_result(position,list):
            size=[float(pos.get('size',0)) for pos in position]
            return any(size)
        logger.warning('Position in coin_in_trade does not list')
        return False

    async def reload_positions(self):
        while self.is_running!=Run.OFF:
            positions=await get_all_position(self.client)
            await self.hp_manager.load_from_redis()
            coins_to_add={}
            for position in positions:
                symbol=position['symbol']
                if position['takeProfit'] and not self.hp_manager.get_main_position(symbol):
                    coins_to_add.setdefault(symbol,{})['main']=position
                    coins_to_add['symbol']=symbol
                elif position['stopLoss'] and not self.hp_manager.get_second_position(symbol):
                    coins_to_add.setdefault(symbol,{})['second']=position
                    coins_to_add['symbol']=symbol
            for position in coins_to_add.values():
                if position.get('main'):
                    order = await self.strategy.get_order(position.get('symbol'),side=position['main']['side'],history=False)
                    await self.hp_manager.set_main_position(position['main'],order_id=order.get('orderId'))
                if position.get('second'):
                    await self.hp_manager.set_secondary_position(position['second'])
            await asyncio.sleep(60)



    async def get_delete_positions(self) -> List[Dict]:
        result_db=self.hp_manager.all_to_dict()
        result_api=await get_all_position(self.client)
        if not result_db:
            return []
        keys = ['symbol', 'size', 'entry_price', 'position_idx',]

        positions_db = pd.DataFrame(result_db)[['symbol', 'size', 'entry_price', 'position_idx','is_main']]
        if result_api:
            positions_api = pd.DataFrame(result_api)[
                ['symbol', 'size', 'avgPrice', 'positionIdx', ]].rename(columns={
                'avgPrice': 'entry_price',
                'positionIdx': 'position_idx'
            }).astype({
                'size': float,
                'entry_price': float,
                'position_idx': int
            })
            keys_from_api = set(tuple(row) for row in positions_api[keys].to_numpy())
            mask = ~positions_db[keys].apply(tuple, axis=1).isin(keys_from_api)
            need_delete = positions_db[mask]
        else:
            need_delete=pd.DataFrame()
        return need_delete.to_dict('records')

    async def check_positions(self):
        try:
            while self.is_running!=Run.OFF:
                need_delete=await self.get_delete_positions()
                if need_delete:
                    for pos in need_delete:
                        is_main=pos.get('is_main',True)
                        symbol=pos.get('symbol')
                        position=None
                        if symbol:
                            if is_main:
                                flag=await self.coin_in_trade(coin=symbol)
                                if not flag:
                                    position=await self.hp_manager.remove_main_position(symbol)
                            else:
                                flag=await self.have_both_side_position(coin=symbol)
                                if not flag:
                                    position=await self.hp_manager.remove_secondary_position(symbol)
                                    await self.strategy.change_tp_main_position(symbol)

                            await self.prepare_and_notification(position,False)
                await asyncio.sleep(5)
        except Exception as e:
            logger.exception(e)


    async def get_worst_positions(self) -> List[Dict]:
        positions=await get_all_position(self.client)
        if positions:
            df = pd.DataFrame(positions)
            df['unrealisedPnl'] = df['unrealisedPnl'].astype('float64')

            symbols_with_2_positions = df['symbol'].value_counts()
            symbols_to_keep = symbols_with_2_positions[symbols_with_2_positions == 2].index

            df_filtered = df[df['symbol'].isin(symbols_to_keep)]

            if not df_filtered.empty:
                symbol = df_filtered.groupby('symbol')['unrealisedPnl'].sum().idxmin()
                return df[df['symbol']==symbol].to_dict(orient='records')
        return []



    async def close_worst_pnl_position(self):
        positions=await self.get_worst_positions()
        if not positions: return
        for pos in positions:
            if pos: await close_order(self.client,pos)




    async def trading_task(self):
        df_info=pd.DataFrame.from_dict(await self.redis_client.get_all_coins_info(),orient='index')
        try:
            while self.is_running!=Run.OFF:
                while self.is_running==Run.ACTIVE:
                    await switch_position_mode(self.client)
                    have_balance=await self.have_balance()
                    if not (have_balance):
                        try:
                            should_close= await self.should_close()
                            if should_close:
                                await self.close_worst_pnl_position()
                        except Exception as e:
                            self.set_client()
                            logger.exception(f"cant close worst pnl positions {e}")
                        await asyncio.sleep(10)
                        continue
                    max_order=self.settings.balance if settings.TRADING_MODE=='auto' else 25
                    if (len(self.hp_manager.positions)>=max_order):
                        await asyncio.sleep(30)
                        continue
                    coins= await self.strategy.get_coins_to_trade()
                    if coins.empty:
                        await asyncio.sleep(10)
                        continue
                    coins = pd.concat([coins,df_info],axis=1,join='inner')
                    coins=coins[coins[['Long','Short']].any(axis=1)]
                    for _,coin in coins.iterrows():
                        if coin.name in self.hp_manager.positions.keys():
                            continue
                        have_balance=await self.have_balance()
                        if have_balance:
                            await asyncio.sleep(np.random.choice(np.linspace(1,3,10)))
                            task=asyncio.create_task(self.strategy.fetch_trade(coin))
                        await asyncio.sleep(0.5)
                    await asyncio.sleep(20)

                await asyncio.sleep(1)

            await asyncio.sleep(5)
        except Exception as e:
            logger.exception(f'CRITICAL ERROR {e}')


    async def start_trade(self):
        tasks = [
            self.check_running(),
            self.check_settings(),
            self.check_positions(),
            self.trading_task(),
            self.reload_positions(),
            self.strategy.all_tasks()
        ]

        for task in tasks:
            self.all_task.append(asyncio.create_task(task))



        try:
            while self.is_running!=Run.OFF:
                await asyncio.sleep(0.5)
        finally:
            await asyncio.sleep(0.2)
            for task in self.all_task:
                try:
                    task.cancel()
                    await asyncio.wait_for(task, timeout=5)

                except asyncio.TimeoutError as er:
                    logger.debug((f"{task.get_name()} took too long to cancel. {er}"))
                except asyncio.CancelledError as er:
                    logger.debug((f"{task.get_name()} Cancelled. {er}"))

            try:
                await self.client.close()
            except Exception as e:
                logger.error(f'Cannot close session client {e}')

