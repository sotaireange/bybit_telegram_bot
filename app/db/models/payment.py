from sqlalchemy import Column, BigInteger, Float, DateTime, func, select, Integer, ForeignKey, Enum as SQLAEnum, update
from typing import Dict

from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum
from dataclasses import dataclass
from ._base import Base




class PaymentStatus(Enum):
    PENDING = "pending"
    SUCCESS = "success"

class PaymentType(Enum):
    UNKNOWN = "unknown"
    FK='free_kassa'
    PK='pay_kassa'


@dataclass
class PaymentOrderData:
    user_id:int
    payment_id:int
    time:int

    def to_str(self):
        return f'user_{self.user_id}-payment_{self.payment_id}-time_{self.time}'

@dataclass
class PaymentSucces:
    order_id: str
    amount: float
    type: PaymentType

    def extract_data(self) -> PaymentOrderData:
        parts = self.order_id.split('-')

        if len(parts) != 3:
            raise ValueError(f"Неверный формат order_id: {self.order_id}")

        user_id = parts[0].replace('user_', '')
        payment_id = parts[1].replace('payment_', '')
        time = parts[2].replace('time_', '')

        return PaymentOrderData(
            user_id=int(user_id),
            payment_id=int(payment_id),
            time=int(float(time))
        )

class Payment(Base):
    """Модель платежей для сохранения в PostgreSQL"""
    __tablename__ = 'payments'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    status = Column(SQLAEnum(PaymentStatus), default=PaymentStatus.PENDING)
    amount = Column(Float, nullable=False)
    created_at = Column(DateTime, default=func.now())
    completed_at = Column(DateTime, nullable=True)
    type= Column(SQLAEnum(PaymentType), default=PaymentType.UNKNOWN)
    user = relationship("User", back_populates="payments")

    def to_dict(self):
        """Преобразование платежа в словарь"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'status': self.status.value,
            'amount': self.amount,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

    def __repr__(self):
        return f"<Payment(id={self.id}, user_id={self.user_id}, status='{self.status}', amount={self.amount})>"

    @staticmethod
    async def get_payment(session: AsyncSession, **kwargs) -> "Payment | None":
        """Получение платежа по заданным критериям"""
        filters = [getattr(Payment, key) == v for key, v in kwargs.items()]
        query = await session.execute(select(Payment).where(*filters))
        return query.scalar_one_or_none()

    @staticmethod
    async def find_or_create_payment(session: AsyncSession, user_id: int) -> "Payment":
        payment=await Payment.get_payment(session, user_id=user_id,status=PaymentStatus.PENDING)

        if not payment:
            payment = Payment(
                user_id=user_id,
                amount=0,
                status=PaymentStatus.PENDING
            )
            session.add(payment)
            await session.commit()
        return payment



    @staticmethod
    async def update_payment(session: AsyncSession, user_id: int, **kwargs) -> "Payment":
        payment=await Payment.find_or_create_payment(session, user_id=user_id)

        if kwargs.get('status') == PaymentStatus.SUCCESS and 'completed_at' not in kwargs:
            kwargs['completed_at'] = func.now()


        for key, value in kwargs.items():
            if hasattr(payment, key):
                setattr(payment, key, value)

        await session.commit()
        await session.refresh(payment)
        return payment

    @staticmethod
    async def get_user_payments(session: AsyncSession, user_id: int) -> list["Payment"]:
        """Получение всех платежей пользователя"""
        query = await session.execute(
            select(Payment)
            .where(Payment.user_id == user_id)
            .order_by(Payment.created_at.desc())
        )
        return list(query.scalars().all())

    @staticmethod
    async def get_pending_payments(session: AsyncSession) -> list["Payment"]:
        """Получение всех ожидающих платежей"""
        query = await session.execute(
            select(Payment)
            .where(Payment.status == PaymentStatus.PENDING)
            .order_by(Payment.created_at.asc())
        )
        return list(query.scalars().all())