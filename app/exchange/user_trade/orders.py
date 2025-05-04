import json
from typing import Dict, Optional, Hashable, List, Union
from dataclasses import dataclass, asdict
from enum import Enum

import pandas as pd
from redis.asyncio import Redis
from .utils import safe_float

from app.db.models import TradeSettings


class PositionIdx(int, Enum):
    LONG = 1
    SHORT = 2

class PositionMain(str, Enum):
    MAIN = 'main'
    HEDGE = 'hedge'

@dataclass
class Position:
    size: float
    amount:float
    entry_price: float
    position_idx: PositionIdx
    tpsl_order_id: str
    updated_time:str


    def to_dict(self):
        result = asdict(self)
        result["position_idx"] = self.position_idx.value
        return result

    @classmethod
    def from_dict(cls, data):
        if "position_idx" in data:
            data["position_idx"] = PositionIdx(data["position_idx"])
        return cls(**data)

@dataclass
class MainPosition(Position):
    take_profit_price: float
    tracking_price: Optional[float] = None

    def to_dict(self):
        result = asdict(self)
        result["position_idx"] = self.position_idx.value
        return result

    @classmethod
    def from_dict(cls, data):
        if "position_idx" in data:
            data["position_idx"] = PositionIdx(data["position_idx"])
        return cls(**data)


@dataclass
class SecondaryPosition(Position):
    stop_loss_price: float

    def to_dict(self):
        result = asdict(self)
        result["position_idx"] = self.position_idx.value
        return result

    @classmethod
    def from_dict(cls, data):
        if "position_idx" in data:
            data["position_idx"] = PositionIdx(data["position_idx"])
        return cls(**data)

@dataclass
class HedgePosition:
    coin: str
    main_position: Optional[MainPosition] = None
    secondary_position: Optional[SecondaryPosition] = None

    def to_dict(self):
        result = {
            "coin": self.coin,
        }
        if self.main_position:
            result["main_position"] = self.main_position.to_dict()
        if self.secondary_position:
            result["secondary_position"] = self.secondary_position.to_dict()
        return result

    @classmethod
    def from_dict(cls, data):
        result = cls(
            coin=data["coin"],
        )
        if "main_position" in data and data["main_position"]:
            result.main_position = MainPosition.from_dict(data["main_position"])
        if "secondary_position" in data and data["secondary_position"]:
            result.secondary_position = SecondaryPosition.from_dict(data["secondary_position"])
        return result



class HedgePositionManager:
    def __init__(self, user_id: int, redis: Redis, settings: TradeSettings):
        self.user_id = user_id
        self.redis = redis
        self.redis_key = f"hedge_positions:{self.user_id}"
        self.positions: Dict[str, HedgePosition] = {}
        self.settings = settings

    async def load_from_redis(self):
        raw_data = await self.redis.hgetall(self.redis_key)
        self.positions = {}

        for coin, position in raw_data.items():
            self.positions[coin] = HedgePosition.from_dict(json.loads(position))


    async def save_position_to_redis(self, coin: str):
        if coin in self.positions:
            position_data = self.positions[coin].to_dict()
            await self.redis.hset(self.redis_key, coin, json.dumps(position_data))
        else:
            await self.redis.hdel(self.redis_key, coin)


    async def save_all_positions_to_redis(self):
        mapping={key: json.dumps(value.to_dict()) for key,value in self.positions.items()}
        await self.redis.hset(self.redis_key, mapping=mapping)


    def get_tracking_price(self, coin: str) -> Optional[float]:
        if coin in self.positions and self.positions[coin].main_position:
            return self.positions[coin].main_position.tracking_price
        return None

    def should_create_hedge(self, coin: str, current_price: float) -> bool:
        position=self.positions.get(coin)
        if position:
            main_position=position.main_position
            secondary_position=position.secondary_position
        else:
            return False
        if coin not in self.positions or not main_position or secondary_position:
            return False

        tracking_price = main_position.tracking_price

        if not tracking_price:
            return False

        if main_position.position_idx == PositionIdx.LONG:
            return current_price <= tracking_price
        else:
            return current_price >= tracking_price


    async def set_main_position(
            self,
            position_data: Dict[str,str],
            take_profit_order_id:str
    ):
        coin = position_data.get("symbol")
        position_idx = PositionIdx(safe_float(position_data.get("positionIdx", 0)))
        size=safe_float(position_data.get('size'))
        position_value=safe_float(position_data.get('positionValue',0))
        leverage=safe_float(position_data.get('leverage',1))
        take_profit=safe_float(position_data.get('takeProfit'))
        entry_price=safe_float(position_data.get('avgPrice'))
        updated_time=position_data.get('updatedTime')
        if leverage==0: leverage=0.01
        amount=position_value/leverage


        if coin not in self.positions:
            self.positions[coin] = HedgePosition(coin=coin)


        if position_idx==PositionIdx.LONG:
            tracking_price = entry_price * (1 - self.settings.hedge_percentage / 100)
        else:
            tracking_price=entry_price * (1 + self.settings.hedge_percentage / 100)

        self.positions[coin].main_position = MainPosition(
            size=size,
            amount=amount,
            position_idx=position_idx,
            entry_price=entry_price,
            take_profit_price=take_profit,
            tpsl_order_id=take_profit_order_id,
            tracking_price=tracking_price,
            updated_time=updated_time,
        )



        await self.save_position_to_redis(coin)


    async def set_secondary_position(
            self,
            position_data: Dict[str,str],
            stop_loss_order_id:str
    ):
        coin = position_data.get("symbol")
        position_idx = PositionIdx(safe_float(position_data.get("positionIdx", 0)))
        size=safe_float(position_data.get('size'))
        position_value=safe_float(position_data.get('positionValue',0))
        leverage=safe_float(position_data.get('leverage',1))
        stop_loss=safe_float(position_data.get('stopLoss'))
        entry_price=safe_float(position_data.get('avgPrice'))
        updated_time=position_data.get('updatedTime')
        if leverage==0: leverage=0.01
        amount=position_value/leverage

        position=self.get_position(coin)
        if position:
            try:
                self.positions[coin].secondary_position = SecondaryPosition(
                    size=size,
                    amount=amount,
                    position_idx=position_idx,
                    entry_price=entry_price,
                    updated_time=updated_time,
                    stop_loss_price=stop_loss,
                    tpsl_order_id=stop_loss_order_id,
                )
                await self.save_position_to_redis(coin)
            except KeyError:
                pass






    async def remove_main_position(self, coin: str) -> Optional[MainPosition]:
        if coin in self.positions:
            pos=self.positions[coin].main_position
            self.positions[coin].main_position = None
            if not self.positions[coin].secondary_position:
                del self.positions[coin]
            await self.save_position_to_redis(coin)
            return pos

    async def remove_secondary_position(self, coin: str) -> Optional[SecondaryPosition]:
        if coin in self.positions:
            pos=self.positions[coin].secondary_position
            self.positions[coin].secondary_position=None
            if not self.positions[coin].main_position:
                del self.positions[coin]
            await self.save_position_to_redis(coin)
            return pos

    async def remove_all_position(self, coin: str) -> Optional[HedgePosition]:
        if coin in self.positions:
            pos=self.positions.pop(coin)
            await self.save_position_to_redis(coin)
            return pos

    async def sync_position_with_db(self,positions: pd.DataFrame):
        df=pd.DataFrame(positions)
        df['updatedTime']=df['updatedTime'].astype(int)
        df.sort_values(by=['symbol','updatedTime'],inplace=True,ascending=[False,True])
        #TODO: что-то типо такого нужно сделать. Если вдруг при входе сихронизировать БД привязка с createdTime

    def get_tp_order(self,coin:str) -> Optional[str]:
        if coin in self.positions:
            return self.positions[coin].main_position.tpsl_order_id


    def get_sl_order(self,coin:str) -> Optional[str]:
        if coin in self.positions:
            return self.positions[coin].secondary_position.tpsl_order_id


    def get_position(self, coin: str) -> Optional[HedgePosition]:
        return self.positions.get(coin)

    def get_main_position(self,coin:Union[str,Hashable]) -> Optional[MainPosition]:
        position=self.positions.get(coin)
        if position is not None and position.main_position:
            return position.main_position


    def get_second_position(self,coin:Union[str,Hashable]) -> Optional[MainPosition]:
        position=self.positions.get(coin)
        if position is not None and position.secondary_position:
            return position.secondary_position


    def get_all_coins(self) -> List[str]:
        return list(self.positions.keys())

    def has_any_position(self, coin: str) -> bool:
        return coin in self.positions

    def has_main_position(self, coin: str) -> bool:
        return coin in self.positions and self.positions[coin].main_position is not None

    def has_secondary_position(self, coin: str) -> bool:
        return coin in self.positions and self.positions[coin].secondary_position is not None

    def all_to_dict(self) -> List:
        result = []
        for coin, hedge_position in self.positions.items():
            main = hedge_position.main_position
            if main:
                pos_dict = main.to_dict()
                pos_dict["symbol"] = coin
                pos_dict["is_main"] = True
                result.append(pos_dict)
            second=hedge_position.secondary_position
            if second:
                pos_dict = second.to_dict()
                pos_dict["symbol"] = coin
                pos_dict["is_main"] = False
                result.append(pos_dict)
        return result





'''    async def update_main_position_take_profit(self, coin: str, take_profit_price: float, take_profit_order_id: Optional[str] = None):
        if coin in self.positions and self.positions[coin].main_position:
            # Удаляем старый ордер, если он был
            old_order_id = self.positions[coin].main_position.take_profit_order_id
            if old_order_id and old_order_id in self.positions[coin].orders:
                self.positions[coin].orders.remove(old_order_id)

            # Обновляем цену тейк-профита
            self.positions[coin].main_position.take_profit_price = take_profit_price

            # Обновляем ID ордера, если передан новый
            if take_profit_order_id:
                self.positions[coin].main_position.take_profit_order_id = take_profit_order_id
                if take_profit_order_id not in self.positions[coin].orders:
                    self.positions[coin].orders.append(take_profit_order_id)

            await self.save_to_redis()

    async def update_secondary_position_stop_loss(self, coin: str, stop_loss_price: float, stop_loss_order_id: Optional[str] = None):
        if coin in self.positions and self.positions[coin].secondary_position:
            # Удаляем старый ордер, если он был
            old_order_id = self.positions[coin].secondary_position.stop_loss_order_id
            if old_order_id and old_order_id in self.positions[coin].orders:
                self.positions[coin].orders.remove(old_order_id)

            # Обновляем цену стоп-лосса
            self.positions[coin].secondary_position.stop_loss_price = stop_loss_price

            # Обновляем ID ордера, если передан новый
            if stop_loss_order_id:
                self.positions[coin].secondary_position.stop_loss_order_id = stop_loss_order_id
                if stop_loss_order_id not in self.positions[coin].orders:
                    self.positions[coin].orders.append(stop_loss_order_id)

            await self.save_to_redis()'''