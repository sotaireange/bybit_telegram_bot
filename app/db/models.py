from ipywidgets import Datetime
from sqlalchemy.sql import func
from sqlalchemy import Column, BigInteger, String, Boolean, select,DateTime,Float,text
from enum import Enum
from dataclasses import dataclass, asdict,fields



from .database import Base



class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, unique=False, nullable=False)
    leverage=Column(Float,default=10)
    take_profit=Column(Float,default=10)
    hedge_percentage=Column(Float,default=10)
    hedge_stop_loss_percentage=Column(Float,default=10)
    size=Column(Float,default=1)
    balance=Column(Float,default=50)
    api=Column(String,default=None)
    secret=Column(String,default=None)
    first_day=Column(DateTime(timezone=True,), server_default=func.now())
    last_sub_time=Column(DateTime(timezone=True,), server_default=text("NOW() + interval '3 days'"))
    sub_until=Column(DateTime(timezone=True,), server_default=text("NOW() + interval '3 days'"))
    is_banned=Column(Boolean, default=False)
    bybit_uid=Column(BigInteger,default=None,unique=True)



    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "sub_until": self.sub_until.isoformat() if self.sub_until else None,
            "is_run": self.is_run,
            "leverage": self.leverage,
            "take_profit": self.take_profit,
            "hedge_percentage": self.hedge_percentage,
            "hedge_stop_loss_percentage": self.hedge_stop_loss_percentage,
            "size": self.size,
            "balance": self.balance,
            "api": self.api,
            "secret": self.secret,
            'bybit_uid':self._bybit_uid
        }

    def __repr__(self):
        return f"User(telegram_id={self.id}, username={self.username})"


    def __str__(self):
        return f'User- {self.username}, id - {self.id}'


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






class Run(str, Enum):
    ACTIVE = "active"
    HEDGE = "hedge"
    OFF = "off"