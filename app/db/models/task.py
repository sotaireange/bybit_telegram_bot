from sqlalchemy import Column, Integer,BigInteger,func, String,Enum as SQLAEnum,select,update, Text, DateTime,ForeignKey ,Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker,relationship
from datetime import timezone,datetime
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum

from ._base import Base


class TaskStatus(str,Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED='failed'


class Task(Base):
    """Модель задачи для сохранения в PostgreSQL"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    worker_id = Column(Integer, nullable=True)
    status = Column(SQLAEnum(TaskStatus), default=TaskStatus.PENDING)
    result = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    user = relationship("User", back_populates="tasks")


    def to_dict(self):
        """Преобразование задачи в словарь для отправки в брокер сообщений"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'worker_id': self.worker_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'status': self.status,
            'result': self.result
        }

    def __repr__(self):
        return f"<Task(id={self.id}, status='{self.status}')>"


    @staticmethod
    async def get_task(session:AsyncSession,**kwargs) -> "Task":
        filters = [*[getattr(Task, key) == v for key, v in kwargs.items()]]
        query = await session.execute(select(Task).where(*filters))
        return query.scalar()

    @staticmethod
    async def create_task(session: AsyncSession, user_id: int) -> "Task":
        task = Task(
            user_id=user_id,
            status=TaskStatus.PENDING
        )
        session.add(task)
        await session.commit()
        return task

    @staticmethod
    async def update(session, task_id: int, **kwargs) -> None:
        filters = [Task.id == task_id]
        kwargs['updated_at'] = func.now()
        await session.execute(update(Task).filter(*filters).values(**kwargs))
        await session.commit()