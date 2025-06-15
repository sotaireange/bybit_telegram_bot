from typing import Dict, Any, Optional,Union
from pydantic import BaseModel
from faststream.redis import RedisBroker
from enum import Enum


from .trade_position import MainPosition,SecondaryPosition

class TaskType(str, Enum):
    MAIN = "main"
    HEDGE = "hedge"

class TaskMessage(BaseModel):
    task_id: int
    task_type: TaskType
    user_id: int
    data: Optional[Dict[str, Any]] = None





class NotificationType(str,Enum):
    POSITION_CLOSE='position_close'
    POSITION_OPEN='position_open'

class TelegramMessage(BaseModel):
    user_id: int
    type:NotificationType
    data: Union[MainPosition,SecondaryPosition]

