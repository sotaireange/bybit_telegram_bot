import asyncio
import logging
from typing import Dict,Any


from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.filters import CommandStart,Command,StateFilter


from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis


from app.db.services import (postgres_db as pdb,
                         RedisClient)
from app.db.models import User, Run


from app.telegram.keyboards import admin as kbrd
from app.telegram.filter import Admin
from app.telegram.fsm import Main,AdminUserSet
from app.telegram.utils.stock_helper import get_user_positions,get_three_month_pnl, check_permissions,close_all_order_user
from app.telegram.handlers.admin.admin_messages import msg

from . import router

logger = logging.getLogger('aiogram')




@router.callback_query(lambda call: call.data.split(':')[0]=='user_sub')
async def admin_give_sub_callback(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminUserSet.SUB)
    data= call.data.split(':')
    text=msg('input_setting',data[0])
    await state.update_data({'user_id': data[1]})
    await call.message.edit_text(text,reply_markup=kbrd.admin_cancel_menu())


@router.message(StateFilter(AdminUserSet.SUB))
async def admin_give_sub_callback(message: Message, state: FSMContext,db: AsyncSession):
    user_id=int(((await state.get_data()).get('user_id',0)))
    try:
        days=int(message.text)
    except Exception as e:
        await message.answer(msg('input_value_error'))
        days=0
    if user_id and days:
        user_id=int(user_id)
        await pdb.extend_subscription(db,user_id,days)
        text_user=msg('user_subscription',days)
        users=await pdb.get_all_users(db)
        await message.answer(msg('input_success',f"Подписка {user_id}", f'+{days} Дней'),reply_markup=kbrd.all_users_menu(users))
        await message.bot.delete_message(chat_id=message.chat.id,message_id=message.message_id)
        await message.bot.delete_message(chat_id=message.chat.id,message_id=message.message_id-1)
        await message.bot.send_message(chat_id=user_id,text=text_user)

    await state.set_state(Main.UNRUN)



@router.callback_query(lambda call: call.data.split(':')[0]=='user_unsub')
async def admin_unsub_callback(call:CallbackQuery, db: AsyncSession):
    user_id=int(call.data.split(':')[1])
    await pdb.unsubscribe(db,user_id)
    text=msg('unsub_success',user_id)
    text_user=msg('user_unsub')
    users=await pdb.get_all_users(db)
    await call.bot.send_message(chat_id=user_id,text=text_user)

    await call.message.edit_text(text=text,reply_markup=kbrd.all_users_menu(users))


@router.callback_query(lambda call: call.data.split(':')[0]=='user_stop')
async def user_list_callback(call:CallbackQuery, db: AsyncSession,redis_client:RedisClient):
    user_id=int(call.data.split(':')[1])
    await redis_client.set_is_run(user_id,Run.HEDGE)
    user=await pdb.get_user(db,user_id)
    text=msg('text_admin_when_stop',user_id)
    has_permissions=await check_permissions(user)
    if has_permissions['status']:
        pnl=await get_three_month_pnl(user)
        text+=msg.get_user_text(user,pnl,False)
    else:
        text=msg.get_user_text(user,{},False)
        text+=msg.get_permission_text(has_permissions)
    text_user=msg('user_when_stop')
    await call.message.edit_text(text,reply_markup=kbrd.user_menu(user))
    await call.bot.send_message(chat_id=user_id,text=text_user)


@router.callback_query(lambda call: call.data.split(':')[0]=='user_exit')
async def admin_settings_callback(call:CallbackQuery, db: AsyncSession,redis_client:RedisClient):
    user_id=int(call.data.split(':')[1])
    await redis_client.set_is_run(user_id,Run.OFF)
    user=await pdb.get_user(db,user_id)
    await asyncio.sleep(1)
    await close_all_order_user(user)

    text=msg('text_admin_when_exit',user_id)
    has_permissions=await check_permissions(user)
    if has_permissions['status']:
        pnl=await get_three_month_pnl(user)
        text+=msg.get_user_text(user,pnl,False)
    else:
        text=msg.get_user_text(user,{},False)
        text+=msg.get_permission_text(has_permissions)
    text_user=msg('user_when_exit')
    await call.message.edit_text(text,reply_markup=kbrd.user_menu(user))
    await call.bot.send_message(chat_id=user_id,text=text_user)


@router.callback_query(lambda call: call.data.split(':')[0]=='user_orders')
async def admin_user_orders_callback(call:CallbackQuery,db: AsyncSession):
    user_id=int(call.data.split(':')[1])
    user= await pdb.get_user(db,user_id)
    positions=await get_user_positions(user)
    text=msg.get_position_text(positions)
    await call.message.edit_text(text,reply_markup=kbrd.user_menu(user),parse_mode='HTML')

