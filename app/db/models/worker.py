from typing import Dict, Any, Optional,Union
from pydantic import BaseModel
from faststream.redis import RedisBroker
from enum import Enum


from .trade_position import MainPosition,SecondaryPosition

# Модели сообщений для очередей
class TaskMessage(BaseModel):
    task_id: int
    task_type: str
    user_id: int
    data: Optional[Dict[str, Any]] = None



class OrderType(str, Enum):
    ACTIVE = "active"
    HEDGE = "hedge"
    OFF = "off"



class TelegramMessage(BaseModel):
    user_id: int
    data: Union[MainPosition,SecondaryPosition]

