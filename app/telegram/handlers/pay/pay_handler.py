import logging

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message,ChatMemberUpdated
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession


from app.telegram import keyboards
from app.telegram.utils.messages import msg
from app.telegram.payments.freekassa import get_payment_url_fk
from app.telegram.payments.paykassa import get_payment_url_pk

from app.db.models import User,Payment,PaymentOrderData
from datetime import datetime,timezone
from . import router
from aiogram import Router
logger = logging.getLogger('aiogram')



#TODO: Так же нужно будет проверять в мидлвари subs,
# если подписка закончилась - не давать включать бота,
# так же раз в час будет проверять юзнеров, у которых закончилась попдиска,
# если закончилась требовать оплатить попдиску


@router.callback_query(lambda call: call.data=='subs_menu',flags={'amount_calculate': True})
async def subs_menu_callback(call: CallbackQuery, user:User,db:AsyncSession,payment:Payment):
    text=msg.get_subs_text(user,payment)
    await call.message.edit_text(text,reply_markup=keyboards.subs_menu(payment.amount))





@router.callback_query(lambda call: call.data=='pay_kassa',flags={'amount_calculate': True})
async def fk_payment_callback(call: CallbackQuery, user:User,db:AsyncSession,payment:Payment):
    time=int(datetime.now(timezone.utc).timestamp())
    order_data=PaymentOrderData(user_id=user.id,payment_id=payment.id,time=time)
    url=await get_payment_url_pk(payment.amount, order_data.to_str())
    if url and payment.amount:
        text=msg.get_subs_text(user,payment)
        await call.message.edit_text(text, reply_markup=keyboards.payment_url(url))
    else:
        text=msg('user_failed_get_url_pk')
        await call.message.edit_text(text=text, reply_markup=keyboards.subs_menu())


@router.callback_query(lambda call: call.data=='free_kassa')
async def fk_payment_callback(call: CallbackQuery, user:User,db:AsyncSession,payment:Payment):
    text=msg.get_subs_text(user,payment)
    url=get_payment_url_fk(5.0, payment.id, user.id)
    await call.message.edit_text(text, reply_markup=keyboards.payment_url(url))
