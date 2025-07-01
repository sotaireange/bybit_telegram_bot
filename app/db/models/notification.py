from sqlalchemy import Column,BigInteger,text,Float ,ForeignKey, String, DateTime, Boolean, func, select
from sqlalchemy.orm import relationship


from ._base import Base



class Notification(Base):
    __tablename__ = "notifications"
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger, ForeignKey('users.id'), nullable=False,index=True)

    main_open = Column(Boolean, default=True)
    main_close = Column(Boolean, default=True)
    hedge_open = Column(Boolean, default=True)
    hedge_close = Column(Boolean, default=True)

    user = relationship("User", back_populates="notification")



    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "main_open": self.main_open,
            "main_close": self.main_close,
            "hedge_open": self.hedge_open,
            "hedge_close": self.hedge_close
        }

    def __repr__(self):
        return f"Notification(telegram_id={self.id})"


    def __str__(self):
        return f'Notification -  id - {self.id}'