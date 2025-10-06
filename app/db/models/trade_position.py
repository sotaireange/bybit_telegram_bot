import pandas as pd
from typing import Optional
from dataclasses import dataclass, asdict
from enum import Enum



class PositionIdx(int, Enum):
    LONG = 1
    SHORT = 2

class PositionType(str, Enum):
    MAIN = 'main'
    HEDGE = 'hedge'

@dataclass
class Position:
    symbol: str
    size: float
    amount:float
    entry_price: float
    position_idx: PositionIdx
    updated_time:str
    position_type: PositionType
    leverage:float
    take_profit_price: Optional[float]=None
    take_stop_orderid:Optional[str]=None

    def to_dict(self):
        result = asdict(self)
        result["position_idx"] = self.position_idx.value
        result["position_type"] = self.position_type.value
        return result

    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        if "position_idx" in data:
            data["position_idx"] = PositionIdx(data["position_idx"])
        if "position_type" in data:
            data["position_type"] = PositionType(data["position_type"])
        return cls(**data)

@dataclass
class MainPosition(Position):
    tracking_price: Optional[float] = None

    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        data.pop('tpsl_order_id', None)
        if "position_idx" in data:
            data["position_idx"] = PositionIdx(data["position_idx"])
        if "position_type" in data:
            data["position_type"] = PositionType(data["position_type"])
        return cls(**data)


@dataclass
class SecondaryPosition(Position):
    stop_loss_price: Optional[float]=None
    stop_loss_orderid:Optional[str]=None

    @classmethod
    def from_dict(cls, data):
        data = data.copy()
        data.pop('tpsl_order_id', None)
        if "position_idx" in data:
            data["position_idx"] = PositionIdx(data["position_idx"])
        if "position_type" in data:
            data["position_type"] = PositionType(data["position_type"])
        return cls(**data)

@dataclass
class HedgePosition:
    coin: str
    entry_timestamp: Optional[pd.Timestamp]=None
    main_position: Optional[MainPosition] = None
    secondary_position: Optional[SecondaryPosition] = None

    def to_dict(self):
        result = {"coin": self.coin}

        if self.entry_timestamp is not None:
            result["entry_timestamp"] = self.entry_timestamp.isoformat()
        if self.main_position:
            result["main_position"] = self.main_position.to_dict()
        if self.secondary_position:
            result["secondary_position"] = self.secondary_position.to_dict()
        return result

    @classmethod
    def from_dict(cls, data):
        kwargs = {"coin": data["coin"]}
        if data.get("entry_timestamp"):
            kwargs["entry_timestamp"] = pd.Timestamp(data["entry_timestamp"])
        if data.get("main_position"):
            kwargs["main_position"] = MainPosition.from_dict(data["main_position"])
        if data.get("secondary_position"):
            kwargs["secondary_position"] = SecondaryPosition.from_dict(data["secondary_position"])

        return cls(**kwargs)