from enum import Enum
from dataclasses import dataclass, asdict,fields


@dataclass
class TradeSettings:
    size: float = 1
    balance: float = 80
    take_profit: float = 3
    hedge_percentage: float = 3
    hedge_stop_loss_percentage: float = 0.5
    leverage: float = 10


    def to_dict(self):
        result = asdict(self)
        return result

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    def update(self, new_data: dict):
        for f in fields(self):
            if f.name in new_data:
                setattr(self, f.name, float(new_data[f.name]))



@dataclass
class CoinSettings:
    volume_long: float = 300_000_000.0
    volume_short: float = 300_000_000.0
    long_percentage: float = 90.0
    short_percentage: float = 10.0
    def to_dict(self):
        result = asdict(self)
        return result

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

