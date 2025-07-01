import time
import asyncio
import logging

from typing import List
from sqlalchemy import Column, Integer,BigInteger,func,and_,Enum as SQLAEnum,select,update, Text, DateTime,ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum

from ._base import Base

from app.db.models.worker import TaskType


logger=logging.getLogger("system")

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
    type=Column(SQLAEnum(TaskType), default=TaskType.MAIN)
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
    async def get_user_task(session: AsyncSession, user_id: int) -> List["Task"]:
        """Получение всех платежей пользователя"""
        query = await session.execute(
            select(Task)
            .where(
                and_(
                    Task.user_id == user_id,
                    Task.status.not_in([TaskStatus.COMPLETED,TaskStatus.FAILED]))
            ))
        return list(query.scalars().all())

    @staticmethod
    async def get_proccesing_tasks(session: AsyncSession) -> list["Task"]:
        """Получение всех ожидающих платежей"""
        result = await session.scalars(
            select(Task).where(Task.status.in_([TaskStatus.PROCESSING])))
        return list(result.all())


    @staticmethod
    async def get_task(session:AsyncSession,**kwargs) -> "Task":
        filters = [*[getattr(Task, key) == v for key, v in kwargs.items()]]
        query = await session.execute(select(Task).where(*filters))
        return query.scalar()

    @staticmethod
    async def create_task(session: AsyncSession, user_id: int,type:TaskType=TaskType.MAIN) -> "Task":
        task = Task(
            user_id=user_id,
            status=TaskStatus.PENDING,
            type=type
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


    @staticmethod
    async def close_all_tasks(session:AsyncSession,user_id:float):
        await session.execute(update(Task)
                              .where(
                                    and_(
                                        Task.user_id==user_id,
                                        Task.status.not_in([TaskStatus.COMPLETED,TaskStatus.FAILED])
                                    ))
                              .values(status=TaskStatus.FAILED,
                                      error='Висячая задача')
                              )

        await session.commit()

    @staticmethod
    async def get_user_task_with_wait(session:AsyncSession,user_id: int,max_wait:int=25) -> None:
        start_time=time.monotonic()
        while True:
            result=await Task.get_user_task(session,user_id)
            if not result:
                return
            if time.monotonic()-start_time>max_wait:
                logger.info(f'User - {user_id} close all Task')
                await Task.close_all_tasks(session,user_id)
                break

            await asyncio.sleep(5)

