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
    size: float
    amount:float
    entry_price: float
    position_idx: PositionIdx
    tpsl_order_id: str
    updated_time:str
    position_type: PositionType


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