from abc import ABC, abstractmethod
from typing import TYPE_CHECKING,Union, Hashable,Dict,List,Optional
import pandas as pd
import logging
import asyncio

if TYPE_CHECKING:
    from ..user_trade import TradeBot # Относительный импорт к вашему файлу

from app.exchange.bybit_async import (get_positions,get_order,
                                      get_mark_price,set_leverage,
                                      get_balance,get_all_position,
                                      place_order,switch_position_mode,
                                      change_tp_price,close_order)
from app.exchange.bybit_async import get_order, place_order

from app.exchange.user_trade.utils import (improved_round_step_size,round_step_size, proof_result)
from app.db.models import Position

logger=logging.getLogger('trading')


class TradingStrategy(ABC):
    def __init__(self, context: 'TradeBot'):
        self.context = context


    def _calculate_position_size(self, position: Union[Dict,Position], price: float, coin: pd.Series) -> float:

        settings = self.context.settings
        if isinstance(position,dict):
            available_balance = float(position.get("totalAvailableBalance", 0))

            amount_in_usdt = max(
                (((settings.size / 100) * available_balance) * settings.leverage),
                5.0
            )

            raw_amount = (amount_in_usdt / price) + coin.qtyStep
            amount_coin = max(
                round_step_size(raw_amount, coin.qtyStep),
                coin.minOrderQty
            )

        else:
            rounded_size = improved_round_step_size(position.size,coin.qtyStep,price,5)
            amount_coin = max(
                rounded_size,
                position.size)

        return amount_coin

    def _calculate_tp_price(self, price: float, tick_size: float, is_long: bool) -> float:
        settings = self.context.settings
        direction_multiplier = 1 if is_long else -1

        price_multiplier = 1 + ((settings.take_profit / 100) * direction_multiplier)
        tp_price = round_step_size(price * price_multiplier, tick_size)
        return tp_price

    def _calculate_sl_price(self, price: float, tick_size: float, is_long_order: bool) -> float:
        settings = self.context.settings
        direction_multiplier = -1 if is_long_order else 1

        price_multiplier = 1 + ((settings.hedge_stop_loss_percentage / 100) * direction_multiplier)
        sl_price = round_step_size(price * price_multiplier, tick_size)
        return sl_price

    async def get_position_due_side(self,coin:Hashable,side:str) -> Dict:
                positions=await get_positions(self.context.client,coin)
                position=[position for position in positions if position.get('side')==side]
                return position[0] if len(position)>0 else {}

    async def get_order(self, coin: Hashable, orderId: Union[str, List] = None,
                        history: bool = True, side: str = '') -> Dict:
        orders = await get_order(self.context.client, coin, history=history, limit=5)

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

    async def _get_confirmed_orders(self, coin: pd.Series,
                                    order_id: Optional[str]=None,
                                    history: bool=True,
                                    side:str='',
                                    max_retries: int = 5) -> Dict[str,str]:
        for i in range(max_retries):
            order_entry = await self.get_order(coin.name, order_id,history=history,side=side)
            if order_entry and order_entry.get('orderStatus') != 'Cancelled':
                return order_entry
            await asyncio.sleep(0.5)
        logger.warning(
            f"User: {self.context.user_id}, Coin: {coin.name} "
            f"Order {order_id} STATUS {order_entry.get('orderStatus')} Side= {side}, History={history} hasn't found or cancelled."
        )
        return {}


    async def get_side_from_order(self,coin: Hashable,order_id: str) -> str:
        order_entry=await self._get_confirmed_orders(coin,order_id)
        side_entry = order_entry.get('side','')
        return side_entry


    async def get_associated_tp_sl_order(self, coin: Hashable, side: str) -> Dict[str,str]:
        """Находит связанный с позицией ордер TP/SL."""
        recent_orders= await self._get_confirmed_orders(coin,side,history=False)
        return recent_orders



    async def _process_successful_order(self, coin: pd.Series, order: Dict, is_hedge: bool = False) -> bool:
        try:
            if not proof_result(order, dict) or order.get('retCode',-1)!=0:
                logger.debug(f'order: {order} symbol: {coin.name}')
                return False

            order=order.get('result',{})
            await asyncio.sleep(1)


            order_entry = await self._get_confirmed_orders(coin, order['orderId'])
            if not order_entry:
                logger.error(f"FAIL GET CONFIRMED ORDER {order['orderId']} for {coin.name}.\n Order : {order}")
                return False

            side_entry = order_entry.get['side']
            tp_sl_order = await self.get_associated_tp_sl_order(coin.name, side_entry)
            if not tp_sl_order:
                logger.error(f"FAIL GET Tp/SL order {coin.name}, entry order {order_entry}")
                return False
            position_data = await self.get_position_due_side(coin.name, side_entry)
            if not position_data:
                logger.error(f"FAIL get Position {coin.name}.")
                return False

            order_id = tp_sl_order.get('orderId')

            if is_hedge:
                position_object = await self.context.hp_manager.set_secondary_position(position_data, order_id=order_id)
            else:
                position_object = await self.context.hp_manager.set_main_position(position_data, order_id=order_id)

            await self.context.prepare_and_notification(position_object,True)
            return True

        except Exception as e:
            logger.exception(f"Критическая ошибка при обработке ордера для {coin}: {e}")
            return False




    @abstractmethod
    async def change_tp_main_position(self,symbol:Hashable):
        pass

    @abstractmethod
    async def get_coins_to_trade(self) -> pd.DataFrame:
        """Get DataFrame with coins to trade depend Manual/Auto strategy"""
        pass

    @abstractmethod
    async def fetch_trade(self,coin:pd.Series):
        """Enter the trade depend of manual/auto strategy"""
        pass


    @abstractmethod
    async def fetch_order(self,coin:pd.Series) -> Dict:
        pass

    @abstractmethod
    async def fetch_hedge_order(self,coin:str) -> Dict:
        pass


    @abstractmethod
    async def all_tasks(self):
        pass