import logging
from typing import Callable, Dict, Awaitable, Any

from aiogram import BaseMiddleware
from aiogram.types import Update


from app.common.config import settings



logger=logging.getLogger('aiogram')

class ManuallyMiddleware(BaseMiddleware):

    def __init__(self):
        super().__init__()

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]],
            Awaitable[Any]],
            event: Update,
            data: Dict[str, Any]
    ) -> Any:
        user_id=event.message.from_user.id
        if user_id in settings.ADMIN_IDS:
            return await handler(event, data)
        return