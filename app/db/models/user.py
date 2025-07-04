from sqlalchemy import Column,BigInteger,text,Float , String, DateTime, Boolean, func, select
from sqlalchemy.orm import relationship


from ._base import Base



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
    pnl=Column(Float,default=0)
    bybit_uid=Column(BigInteger,default=None,unique=True)
    bybit_sub_account_uid=Column(BigInteger,default=None)


    tasks = relationship("Task", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    notification = relationship("Notification", back_populates="user", uselist=False)



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
            "pnl": self.pnl,
            'bybit_uid':self._bybit_uid,
            'bybit_sub_account_uid': self.bybit_sub_account_uid,

        }

    def __repr__(self):
        return f"User(telegram_id={self.id}, username={self.username})"


    def __str__(self):
        return f'User- {self.username}, id - {self.id}'