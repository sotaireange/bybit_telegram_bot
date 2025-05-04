import logging
from typing import Callable, Dict, Awaitable, Any


from aiogram import BaseMiddleware
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

from redis.asyncio import Redis

from app.db.services import RedisClient


from app.telegram.utils.messages import msg
from app.telegram.keyboards import cancel_menu

logger=logging.getLogger('telegram')


class AdminSetValueMiddleware(BaseMiddleware):
    def __init__(self, redis:Redis):
        super().__init__()
        self.redis_client = RedisClient(redis)

    async def __call__(
            self,
            handler: Callable[[Message, Dict[str, Any]],
            Awaitable[Any]],
            event: Message,
            data: Dict[str, Any]
    ) -> Any:
        value = event.text
        state: FSMContext = data.get("state")
        if not value or state is None:
            logger.error('Invalid state ')
            return

        current_state = (await state.get_state()).lower().split(":")
        if current_state[0]=='adminset':
            state_key = current_state[1]
            try:
                value = float(value)
            except ValueError:
                return await event.answer(msg('input_value_error'),reply_markup=cancel_menu())

            await self.redis_client.set(state_key,value)
        else:
            logger.debug("Not state SET")
        return await handler(event, data)