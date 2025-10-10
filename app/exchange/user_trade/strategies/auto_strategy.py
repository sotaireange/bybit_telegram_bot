import pandas as pd
from .base import TradingStrategy
from typing import TYPE_CHECKING,Hashable,Dict
import logging
import asyncio

if TYPE_CHECKING:
    from ..user_trade import TradeBot



from app.exchange.user_trade.utils import (improved_round_step_size,round_step_size, proof_result)
from app.exchange.bybit_async import (get_positions,get_order,
                                      get_mark_price,set_leverage,
                                      get_balance,get_all_position,
                                      place_order,switch_position_mode,
                                      change_tp_price,close_order)

from app.db.models import Run,PositionIdx


logger=logging.getLogger('trading')



class AutoTradingStrategy(TradingStrategy):
    def __init__(self, context: 'TradeBot'):
        super().__init__(context)

    async def change_tp_main_position(self,symbol:Hashable) -> None:
        position=self.context.hp_manager.get_main_position(symbol)
        if not position: return
        order_id=position.take_stop_orderid
        price_multiplier = 1 + ((self.context.settings.hedge_stop_loss_percentage / 100) * (1 if position.position_idx==PositionIdx.LONG else -1))
        coin_info=(await self.context.redis_client.get_coin_info(symbol))[symbol]
        tp_price = round_step_size(position.take_profit_price * price_multiplier, coin_info.get('tickSize',0))
        response={}
        try:
            if order_id:
                response=await change_tp_price(self.context.client,symbol,order_id,tp_price)
                if self.context.hp_manager.get_main_position(symbol):
                    await self.context.hp_manager.update_main_position_take_profit(symbol,tp_price)

        except Exception as e:
            logger.error(f'Cannot change tp_price\nResponse:{response} \n {e}')


    async def get_coins_to_trade(self) -> pd.DataFrame:
        coins=pd.DataFrame.from_dict(await self.context.redis_client.get_coins(),orient='index')
        return coins


    async def fetch_hedge_order(self,coin:pd.Series) -> Dict:
        try:
            price=await get_mark_price(self.context.client,coin.name)

            if price == 0:
                return {}

            position=self.context.hp_manager.get_main_position(coin.name)
            is_long=position.position_idx==PositionIdx.SHORT
            amount=self._calculate_position_size(position=position,price=price,coin=coin)
            sl_price=self._calculate_sl_price(price,coin.tickSize,is_long)


            order = (await place_order(
                self.context.client,
                coin.name,
                amount,
                is_long,
                sl_price=sl_price
            ))


            return order


        except Exception as e:
            logger.exception(e)


    async def fetch_order(self, coin: pd.Series) -> Dict:
        try:
            if await self.context.coin_in_trade(coin.name):
                logger.debug(f"{coin.name} is trading. Pass.")
                return {}

            balance = await get_balance(self.context.client)
            price=await get_mark_price(self.context.client,coin.name)
            if not (proof_result(balance, dict) and price > 0):
                logger.warning(
                    f"Cannot get balance/price in fetch_coin\n"
                    f"Price: {price}, Balance: {type(balance)}"
                )
                return {}


            amount=self._calculate_position_size(balance,price,coin
            )
            tp_price=self._calculate_tp_price(price,coin.tickSize,coin.Long)

            order = (await place_order(
                self.context.client,
                coin.name,
                amount,
                coin.Long,
                tp_price=tp_price
            ))


            return order


        except Exception as e:
            logger.exception(e)

    async def fetch_trade(self,coin: pd.Series) -> None:
        await set_leverage(self.context.client, coin.name, leverage=self.context.settings.leverage)

        order=await self.fetch_order(coin)
        succes=await self._process_successful_order(coin, order)
        if succes:
            pass
        else:
            logger.warning(f'Failed to process order: {coin.name}, {order}')

    async def check_hedge(self):
        while self.context.is_running!=Run.OFF:
            await asyncio.sleep(2)
            for coin in self.context.hp_manager.get_all_coins():
                try:
                    price=await self.context.redis_client.get_mark_price_coin(coin)
                    should_hedge=self.context.hp_manager.should_create_hedge(coin,price)
                    if should_hedge:
                        have_both_position=await self.context.have_both_side_position(coin)
                        if not have_both_position:
                            have_one_position= await self.context.coin_in_trade(coin)
                            if have_one_position:
                                coin_series=pd.Series((await self.context.redis_client.get_coin_info(coin))[coin],name=coin)
                                order=await self.fetch_hedge_order(coin_series)
                                succes=await self._process_successful_order(coin, order,is_hedge=True)
                except Exception as e:
                    logger.exception(e)
                await asyncio.sleep(0.1)
            await asyncio.sleep(5)

    async def all_tasks(self):
        tasks=[self.check_hedge()]
        await asyncio.gather(*tasks)