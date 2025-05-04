import logging
import asyncio
from typing import Dict,Optional, Hashable, List,Union

import numpy as np
import pandas as pd
from redis.asyncio import Redis

from app.db.services import RedisClient
from app.db.models import Run,TradeSettings


from app.exchange.bybit_async import BybitRequester
from app.exchange.bybit_async import get_positions,get_order,get_mark_price,set_leverage,get_balance,get_all_position, place_order,switch_position_mode

from app.exchange.user_trade.utils import (round_step_size, proof_result)
from app.exchange.user_trade.orders import HedgePositionManager,PositionIdx

logger=logging.getLogger('trading')


import sys
if sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class TradeBot:
    def __init__(self,user_id:int,user_data: Dict,redis: Redis,redis_client:RedisClient):
        self.is_running: Run= Run.ACTIVE

        self.user_id = user_id
        self.client: Optional[BybitRequester] = None
        self.api_key = user_data.get('api_key')
        self.api_secret = user_data.get('api_secret')

        self.settings: TradeSettings= TradeSettings()

        self.redis=redis
        self.redis_client=redis_client
        self.hp_manager:HedgePositionManager

        self.is_notification=True

        self.all_task=[]


    def set_client(self,testnet:bool = False):
        self.client:BybitRequester=BybitRequester(self.api_key,self.api_secret,testnet=testnet)


    async def update_settings(self):
        self.settings.update((await self.redis_client.get_all_trade_settings()).to_dict())


    async def init_hp_manager(self):
        self.hp_manager=HedgePositionManager(self.user_id,self.redis,self.settings)
        await self.hp_manager.load_from_redis()


    async def initialize(self):
        self.set_client(True)
        await self.update_settings()
        await self.init_hp_manager()


    async def check_settings(self):
        while self.is_running!=Run.OFF:
            await self.update_settings()
            await asyncio.sleep(1)


    async def check_running(self):
        while True:
            self.is_running=Run(await self.redis_client.get_is_run(self.user_id))
            await asyncio.sleep(1)
            if self.is_running==Run.OFF:
                break


    async def have_balance(self):
        balance=await get_balance(self.client)
        if proof_result(balance,dict):
            available_balance=float(balance.get('totalAvailableBalance',0))
            total_balance=float(balance.get('totalMarginBalance',1))
            return available_balance/(total_balance+0.000000001) > 0.45
        logger.warning('Balance in have_balance does not dict')
        return False


    async def get_position_due_side(self,coin:Hashable,side:str) -> Dict:
        positions=await get_positions(self.client,coin)
        position=[position for position in positions if position['side']==side]
        return position[0] if len(position)>0 else {}

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
        return True


    async def get_order(self, coin: Hashable, orderId: Union[str, List] = None,
                        history: bool = True, side: str = '') -> Dict:
        orders = await get_order(self.client, coin, history=history, limit=5)

        if not isinstance(orders, list):
            logger.warning('Orders_list in get_order is not a LIST')
            return {}

        if not orders:
            return {}

        df = pd.DataFrame(orders)

        if orderId:
            if isinstance(orderId, list):
                df = df[df['orderId'].isin(orderId)]
            else:
                df = df[df['orderId'] == orderId]

        if side!='':
            df = df[((df['side'] != side) & (df['stopOrderType'].isin(['TakeProfit', 'StopLoss'])))]
        order_records = df.to_dict(orient='records')
        return order_records[0] if order_records else {}

    async def check_hedge(self):
        while self.is_running!=Run.OFF:
            for coin in self.hp_manager.get_all_coins():
                try:
                    price=await self.redis_client.get_mark_price_coin(coin)
                    should_hedge=self.hp_manager.should_create_hedge(coin,price)
                    if should_hedge:
                        have_both_position=await self.have_both_side_position(coin)
                        if not have_both_position:
                            await self.fetch_hedge_coin(coin)
                except Exception as e:
                    logger.exception(e)
                await asyncio.sleep(0.1)
            await asyncio.sleep(5)


    async def fetch_hedge_coin(self,coin:str):
        try:
            coin=pd.Series((await self.redis_client.get_coin_info(coin))[coin],name=coin)
            #price = float(await self.redis_client.get_mark_price_coin(coin.name))
            price=await get_mark_price(self.client,coin.name)
            if price == 0:
                return

            position=self.hp_manager.get_main_position(coin.name)

            is_long=position.position_idx==PositionIdx.SHORT
            price_multiplier = 1 + ((self.settings.hedge_stop_loss_percentage / 100) * (1 if not is_long else -1))
            sl_price = round_step_size(price * price_multiplier, coin.tickSize)

            order = (await place_order(
                self.client,
                coin.name,
                position.size,
                is_long,
                sl_price=sl_price
            ))
            # if order['retCode']==10001:
            #     logger.error(f'Failed to fetch coin {coin.name}\n'
            #                  f'Price{price}\n'
            #                  f'order:{order}')

            order=order["result"]
            if not proof_result(order, dict):
                return

            await asyncio.sleep(1)
            await self.after_fetch_coin(coin.name, order,is_hedge=True)

        except Exception as e:
            logger.exception(e)



    async def check_positions(self):
        try:
            while self.is_running!=Run.OFF:
                need_delete=await self.get_delete_positions()
                if need_delete:
                    for pos in need_delete:
                        is_main=pos.get('is_main',True)
                        symbol=pos.get('symbol')

                        if symbol:
                            if is_main:
                                position=await self.hp_manager.remove_main_position(symbol)
                            else:
                                position=await self.hp_manager.remove_secondary_position(symbol)

                            if self.is_notification:
                                #order=await self.get_order(symbol,orderId=position.tpsl_order_id)
                                logger.debug(f'Position {'MAIN' if is_main else 'SECOND'} is over, coin {symbol}')
                await asyncio.sleep(5)
        except Exception as e:
            logger.error(e)

    async def get_delete_positions(self) -> List[Dict]:
        result_db=self.hp_manager.all_to_dict()
        result_api=await get_all_position(self.client)
        if not result_api[0] or not result_db:
            return [{}]
        positions_db = pd.DataFrame(result_db)[['symbol', 'size', 'entry_price', 'position_idx','is_main']]
        positions_api = pd.DataFrame(result_api)[
            ['symbol', 'size', 'avgPrice', 'positionIdx', ]].rename(columns={
            'avgPrice': 'entry_price',
            'positionIdx': 'position_idx'
        }).astype({
            'size': float,
            'entry_price': float,
            'position_idx': int
        })
        keys = ['symbol', 'size', 'entry_price', 'position_idx',]
        keys_from_api = set(tuple(row) for row in positions_api[keys].to_numpy())
        mask = ~positions_db[keys].apply(tuple, axis=1).isin(keys_from_api)
        need_delete = positions_db[mask]
        return need_delete.to_dict('records')



    async def after_fetch_coin(self, coin: Hashable, order: Dict, is_hedge: bool = False):
        try:
            order_entry = await self.get_order(coin, order['orderId'])
            if not order_entry or order_entry['orderStatus'] == 'Cancelled':
                #logger.debug(f"User: {self.user_id} Coin: {coin} hasn't order status {order_entry.get('orderStatus')}")
                return
            side_entry = order_entry['side']


            recent_orders = await self.get_order(coin,side=side_entry,history=False)

            if not recent_orders:
                order_type = "tp_order" if is_hedge else "sl_order"
                logger.warning(
                    f"User: {self.user_id} Coin: {coin} without {order_type} \n"
                    f"but have order_entry: {order_entry.get('orderId')} - {order_entry.get('orderStatus')}"
                )
                return

            position = await self.get_position_due_side(coin, side_entry)
            if isinstance(position, dict) and position:
                if is_hedge:
                    await self.hp_manager.set_secondary_position(position, recent_orders['orderId'])
                else:
                    await self.hp_manager.set_main_position(position, recent_orders['orderId'])
                logger.debug(f'Set {'hedge' if is_hedge else 'main'} position {coin}')

        except Exception as e:
            logger.exception(f"Error processing {coin}: {e}")




    async def fetch_coin(self, coin: pd.Series) -> None:
        try:
            if await self.coin_in_trade(coin.name):
                logger.debug(f"{coin.name} is trading. Pass.")
                return

            await set_leverage(self.client, coin.name, leverage=self.settings.leverage)

            balance = await get_balance(self.client)
            price = float(await self.redis_client.get_mark_price_coin(coin.name))
            price=await get_mark_price(self.client,coin.name)
            if not (proof_result(balance, dict) and price > 0):
                logger.warning(
                    f"Cannot get balance/price in fetch_coin\n"
                    f"Price: {price}, Balance: {type(balance)}"
                )
                return

            available_balance = float(balance.get("totalMarginBalance", 0))
            raw_amount = ((self.settings.size / 100) * available_balance) * self.settings.leverage / price
            amount_coin = max(
                round_step_size(raw_amount, coin.qtyStep),
                coin.minOrderQty
            )

            price_multiplier = 1 + ((self.settings.take_profit / 100) * (1 if coin.Long else -1))
            tp_price = round_step_size(price * price_multiplier, coin.tickSize)

            order = (await place_order(
                self.client,
                coin.name,
                amount_coin,
                coin.Long,
                tp_price=tp_price
            ))
            # if order['retCode']==10001:
            #     logger.error(f'Failed to fetch coin {coin.name}\n'
            #                  f'Price{price}\n'
            #                  f'order:{order}')

            order=order["result"]
            if not proof_result(order, dict):
                return

            await asyncio.sleep(1)
            await self.after_fetch_coin(coin.name, order)

        except Exception as e:
            logger.exception(e)




    async def start_trade(self):
        tasks = [
            self.check_running(),
            self.check_settings(),
            self.check_hedge(),
            self.check_positions()
        ]

        for task in tasks:
            self.all_task.append(asyncio.create_task(task))


        df_info=pd.DataFrame.from_dict(await self.redis_client.get_all_coins_info(),orient='index')

        try:
            while self.is_running!=Run.OFF:
                while self.is_running==Run.ACTIVE:
                    await switch_position_mode(self.client)

                    if not (await self.have_balance()) or len(self.hp_manager.positions)>80:
                        await asyncio.sleep(120)
                        logger.warning("Haven't Balance or orders>80")
                        continue

                    coins=pd.DataFrame.from_dict(await self.redis_client.get_coins(),orient='index')
                    coins = pd.concat([coins,df_info],axis=1,join='inner')
                    coins=coins[coins[['Long','Short']].any(axis=1)]
                    logger.debug(f'Coins found {len(coins)}')
                    for _,coin in coins.iterrows():
                        if coin.name in self.hp_manager.positions.keys():
                            continue

                        await asyncio.sleep(np.random.choice(np.linspace(1,3,10)))
                        task=asyncio.create_task(self.fetch_coin(coin))

                    await asyncio.sleep(10)

                await asyncio.sleep(1)

            await asyncio.sleep(5)
        finally:
            for task in self.all_task:
                try:
                    task.cancel()
                    await asyncio.wait_for(task, timeout=20)

                except asyncio.TimeoutError as er:
                    logger.error((f"{task.get_name()} took too long to cancel. {er}"))
                except asyncio.CancelledError as er:
                    logger.error((f"{task.get_name()} Cancelled. {er}"))

            try:
                await self.client.close()
            except Exception as e:
                logger.error(f'Cannot close session client {e}')


