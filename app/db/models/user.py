from sqlalchemy import Column, BigInteger, text, Float, String, DateTime, Boolean, func, select, ForeignKey
from sqlalchemy.orm import relationship

from ._base import Base


class UserAPI(Base):
    __tablename__ = "user_apis"
    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name=Column(String,default='main')
    api = Column(String, nullable=True)
    secret = Column(String, nullable=True)
    run = Column(Boolean, default=True)

    user = relationship("User", back_populates="apis")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "api": self.api,
            "secret": self.secret,
            "run": self.run
        }

    def __repr__(self):
        return f"<UserAPI(user_id={self.user_id}, api=****)>"

class User(Base):
    __tablename__ = "users"
    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(String, unique=False, nullable=False)
    leverage = Column(Float, default=10)
    take_profit = Column(Float, default=10)
    hedge_percentage = Column(Float, default=10)
    hedge_stop_loss_percentage = Column(Float, default=10)
    size = Column(Float, default=1)
    balance = Column(Float, default=50)
    first_day = Column(DateTime(timezone=True), server_default=func.now())
    last_sub_time = Column(DateTime(timezone=True), server_default=text("NOW() + interval '3 days'"))
    sub_until = Column(DateTime(timezone=True), server_default=text("NOW() + interval '3 days'"))
    is_banned = Column(Boolean, default=False)
    pnl = Column(Float, default=0)
    bybit_uid = Column(BigInteger, default=None, unique=True)
    bybit_sub_account_uid = Column(BigInteger, default=None)

    tasks = relationship("Task", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    notification = relationship("Notification", back_populates="user", uselist=False)
    apis = relationship("UserAPI", back_populates="user", cascade="all, delete-orphan")


    def get_api(self, api_name: str | None = None) -> UserAPI | None:
        """Возвращает UserAPI по ключу или единственный, если он один."""
        if api_name is not None:
            return next((a for a in self.apis if a.name == api_name), None)
        if len(self.apis) == 1:
            return self.apis[0]
        return None

    def pick_api(self, api: str | None = None) -> UserAPI | None:
        """Возвращает API по ключу или первый из списка, если ключ не задан."""
        if not self.apis:
            return None
        return self.get_api(api) if api else self.apis[0]


    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "sub_until": self.sub_until.isoformat() if self.sub_until else None,
            "is_run": self.is_run,  # Now properly defined
            "leverage": self.leverage,
            "take_profit": self.take_profit,
            "hedge_percentage": self.hedge_percentage,
            "hedge_stop_loss_percentage": self.hedge_stop_loss_percentage,
            "size": self.size,
            "balance": self.balance,
            "pnl": self.pnl,
            'bybit_uid': self.bybit_uid,  # Fixed: removed underscore
            'bybit_sub_account_uid': self.bybit_sub_account_uid,
        }

    def __repr__(self):
        return f"User(telegram_id={self.id}, username={self.username})"

    def __str__(self):
        return f'User- {self.username}, id - {self.id}'


