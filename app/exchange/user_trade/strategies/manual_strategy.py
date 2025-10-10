import pandas as pd
from .base import TradingStrategy
from typing import TYPE_CHECKING, Hashable, Dict
import logging
import asyncio


if TYPE_CHECKING:
    from ..user_trade import TradeBot


from app.exchange.user_trade.utils import (improved_round_step_size,round_step_size, proof_result)
from app.exchange.bybit_async import (get_positions,get_order,
                                      get_mark_price,set_leverage,
                                      get_balance,get_all_position,
                                      place_order,switch_position_mode,
                                      change_tp_price,close_order,
                                      add_tp_price)

from app.db.models import Run,PositionIdx,MainPosition


logger=logging.getLogger('trading')


class ManualTradingStrategy(TradingStrategy):
    def __init__(self, context: 'TradeBot'):
        super().__init__(context)



    async def change_tp_main_position(self,symbol:Hashable):
        position=self.context.hp_manager.get_main_position(symbol)
        if not position: return
        response={}
        try:
            coin=position.symbol
            price_multiplier = 1 + ((self.context.settings.hedge_stop_loss_percentage / 100) * (1 if position.position_idx==PositionIdx.LONG else -1))
            coin_info=(await self.context.redis_client.get_coin_info(coin))[coin]
            tp_price = round_step_size(position.entry_price * price_multiplier, coin_info.get('tickSize',0))
            if self.context.hp_manager.get_main_position(coin):
                if (not self.context.have_both_side_position(coin)) and self.context.coin_in_trade(coin):
                    await add_tp_price(self.context.client,coin,True,tp_price)
                    if self.context.hp_manager.get_main_position(coin):
                        await self.context.hp_manager.update_main_position_take_profit(coin,tp_price)
        except Exception as e:
            logger.error(f'Cannot change tp_price\nResponse:{response} \n {e}')
        finally:
            return response


    async def get_coins_to_trade(self) -> pd.DataFrame:
        # coins=pd.DataFrame.from_dict(await self.context.redis_client.get_coins_with_delete_by_user(user_id=self.context.user_id),orient='index')
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
            tp_price=self._calculate_tp_price(price,coin.tickSize,is_long)


            order = (await place_order(
                self.context.client,
                coin.name,
                amount,
                is_long,
                tp_price=tp_price
            ))


            return order


        except Exception as e:
            logger.exception(e)


    async def fetch_order(self,coin:pd.Series) -> Dict:
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


            amount=self._calculate_position_size(balance,price,coin)

            order = (await place_order(
                self.context.client,
                coin.name,
                amount,
                coin.Long,
            ))
            return order


        except Exception as e:
            logger.exception(e)


    async def approve_hedge(self,coin:pd.Series):
        hp_manager=self.context.hp_manager
        if hp_manager.get_main_position(coin.name) and not (hp_manager.get_second_position(coin)):
            for i in range(5):
                try:
                    if (await self.context.coin_in_trade(coin.name)) and not (await self.context.have_both_side_position(coin.name)):
                        hedge_order=await self.fetch_hedge_order(coin)
                        succes_hedge=await self._process_successful_order(coin,hedge_order)
                        if succes_hedge:
                            return
                except Exception as e:
                    logger.error(f'Error when approve_hedge \n {e}')
                await asyncio.sleep(1)
            logger.warning(f'Failed approvee hedge {coin.name}')




    async def fetch_trade(self,coin:pd.Series):

        await set_leverage(self.context.client, coin.name, leverage=self.context.settings.leverage)

        order=await self.fetch_order(coin)
        succes=await self._process_successful_order(coin, order)
        if succes:
            hedge_order=await self.fetch_hedge_order(coin)
            succes_hedge=await self._process_successful_order(coin,hedge_order)
            if not succes_hedge:
                logger.warning(f'Failed to process hedge order after main order {coin.name}\n {order}')

        else:
            logger.warning(f'Failed to process order: {coin.name}, {order}')
            await self.approve_hedge(coin)


    async def check_time_expired(self):
        hp_manager=self.context.hp_manager
        while self.context.is_running!=Run.OFF:
            for symbol in hp_manager.get_all_coins():
                try:
                    if hp_manager.should_close_order(symbol) and self.context.coin_in_trade(symbol):
                        positions=(await get_positions(self.context.client,symbol))
                        tasks=[]
                        for pos in positions:
                            if pos:
                                tasks.append(close_order(self.context.client,pos))

                        await asyncio.gather(*tasks)
                        await hp_manager.remove_all_position(symbol)
                except Exception as e:
                    logger.error(f'Error while check_time_expired {e}')

                await asyncio.sleep(0.2)

            await asyncio.sleep(10)

    async def all_tasks(self):
        tasks= [self.check_time_expired()]

        await asyncio.gather(*tasks)