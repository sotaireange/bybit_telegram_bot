from aiogram.exceptions import TelegramForbiddenError
from functools import wraps
from typing import Callable, Any, Coroutine

import logging
from app.db.database import AsyncSessionLocal,r as redis
from app.db.services import RedisClient, postgres_db as pdb
from app.db.models import Run

redis_client= RedisClient(redis)

def catch_forbidden():
    """
    Декоратор, ловящий ошибку TelegramForbiddenError и выполняющий действия.
    Ожидается, что декорируемая функция получает user_id как аргумент.
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, Any]]):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except TelegramForbiddenError:
                # Попытка вытащить user_id из args/kwargs
                user_id = kwargs.get("chat_id") or kwargs.get("user_id")

                if user_id is None and args:
                    user_id = args[0]

                logging.warning(f"[Forbidden] User {user_id} заблокировал бота")
                await redis_client.set_is_run(user_id, Run.OFF)
                async with AsyncSessionLocal() as db:
                    await pdb.update_user_fields(db,user_id,{'is_banned': True})
        return wrapper
    return decorator
