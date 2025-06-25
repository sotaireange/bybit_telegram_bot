import logging
from typing import Callable, Dict, Awaitable, Any

from datetime import datetime,timezone,timedelta
from aiogram import BaseMiddleware
from aiogram.types import Update,Message
from aiogram.fsm.context import FSMContext
from aiogram.dispatcher.flags import get_flag

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.services import postgres_db as pdb,RedisClient
from app.db.models import User,Payment


from app.telegram.utils.messages import msg
from app.telegram.keyboards import main_menu,cancel_menu
from app.telegram.utils.pnl_helper import get_user_pnl
from app.telegram.utils.stock_helper import check_permissions

logger=logging.getLogger('aiogram')

class PaymentAmountMiddleware(BaseMiddleware):

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
        logger.info('In PaymenyMiddleware')
        check_payment = get_flag(data, "amount_calculate")

        async with self.sessionmaker() as session:
            user=await pdb.get_user(session,event.from_user.id)



        amount_to_pay=0
        if check_payment:
            permission=await check_permissions(user)
            if permission['status'] and user:
                df_pnl=await get_user_pnl(user,use_last_sub_day=True)

                amount_to_pay=round(df_pnl['closedPnl'].sum(),2) if len(df_pnl) else 0
            else:
                amount_to_pay=0
        if amount_to_pay <=0:
            async with self.sessionmaker() as session:
                time=int(datetime.now(timezone.utc).timestamp())
                user=await pdb.extend_subscription_due_time(session,user_id=user.id,time=time)
                text=msg('payment_not_need')

            return await event.message.edit_text(text,reply_markup=cancel_menu())

        async with self.sessionmaker() as session:
            if amount_to_pay:
                payment= await Payment.update_payment(session,user_id=user.id,amount=amount_to_pay)
            else:
                payment= await Payment.find_or_create_payment(session,user_id=user.id)

        data['payment']=payment



        return await handler(event, data)