import logging
from typing import Callable, Dict, Awaitable, Any


from aiogram import BaseMiddleware
from aiogram.types import Update,Message
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.flags import get_flag

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.services import postgres_db as pdb,RedisClient
from app.db.models import User


from app.telegram.utils.limit import Limit
from app.telegram.utils.messages import msg
from app.telegram.keyboards import cancel_menu



logger=logging.getLogger('telegram')

class DatabaseMiddleware(BaseMiddleware):

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        super().__init__()
        self.sessionmaker = sessionmaker

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]],
            Awaitable[Any]],
            event: Update,
            data: Dict[str, Any]
    ) -> Any:
        async with self.sessionmaker() as session:
            data["db"] = session
            return await handler(event, data)


class RedisMiddleware(BaseMiddleware):
    def __init__(self,redis: Redis):
        super().__init__()
        self.redis=redis

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]],
            Awaitable[Any]],
            event: Update,
            data: Dict[str, Any]
    ) -> Any:
        data["redis_client"] = RedisClient(self.redis)
        return await handler(event, data)


class GetUsereMiddleware(BaseMiddleware):

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]):
        super().__init__()
        self.sessionmaker = sessionmaker

    async def __call__(
            self,
            handler: Callable[[Update, Dict[str, Any]],
            Awaitable[Any]],
            event: Update,
            data: Dict[str, Any]
    ) -> Any:
        async with self.sessionmaker() as session:
            create_user = get_flag(data, "create")
            if create_user:
                await pdb.create_new_user(session,event.from_user)
            user:User=await pdb.get_user(session,event.from_user.id)
            await pdb.update_user_fields(session,event.from_user.id,{'is_banned':False})
            data["user"] = user
            return await handler(event, data)




class SetValueMiddleware(BaseMiddleware):
    def __init__(self, session_maker):
        super().__init__()
        self.session_maker = session_maker

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
        if current_state[0]=='set':
            state_key = current_state[1]
            min_limit, max_limit = getattr(Limit, state_key.upper(), (0,0))
            logger.debug(f'Succes {value} State {state_key} MIN {min_limit} MAX {max_limit}')
            try:
                if state_key not in ['api','secret']:
                    value = float(value)
                    if value > max_limit or value < min_limit:
                        text=msg('input_failure',value,min_limit,max_limit)

                        return await event.answer(text,reply_markup=cancel_menu())
            except ValueError:
                return await event.answer(msg('input_value_error'),reply_markup=cancel_menu())

            async with self.session_maker() as session:
                user:User=await pdb.get_user(session,event.from_user.id)
                data["user"] = user
                await pdb.update_user_fields(db=session, user_id=event.from_user.id,fields_dict={state_key:value})
        else:
            logger.debug("Not state SET")
        return await handler(event, data)