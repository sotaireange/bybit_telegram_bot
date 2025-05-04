import logging


from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command


from sqlalchemy.ext.asyncio import AsyncSession


from app.db.services import (postgres_db as pdb,
                        RedisClient)

from app.telegram.keyboards import admin as kbrd
from app.telegram.filter import Admin
from app.telegram.utils.stock_helper import get_three_month_pnl,check_permissions

from .admin_messages import msg


from . import router

logger = logging.getLogger('aiogram')
from app.telegram.fsm import Main


@router.message(Command('admin'),Admin())
async def admin_menu_start(message: Message):
    text=msg.get_admin_menu_text()
    await message.answer(text,reply_markup=kbrd.admin_menu())



@router.callback_query(lambda call: call.data=='admin_menu')
async def admin_menu_callback(call: CallbackQuery, state: FSMContext):
    await state.set_state(Main.UNRUN)
    text=msg.get_admin_menu_text()
    await call.message.edit_text(text,reply_markup=kbrd.admin_menu())


@router.callback_query(lambda call: call.data=='users')
async def users_list_callback(call:CallbackQuery, db: AsyncSession,redis_client:RedisClient):
    users=await pdb.get_all_users(db)
    list_running=await redis_client.get_all_is_run()
    text=msg.get_user_admin_text(users,list_running)
    await call.message.edit_text(text=text,reply_markup=kbrd.all_users_menu(users))


@router.callback_query(lambda call: call.data.split(':')[0]=='user')
async def user_list_callback(call:CallbackQuery, db: AsyncSession,redis_client:RedisClient):
    user_id=int(call.data.split(':')[1])
    is_run= await redis_client.get_is_run(user_id)
    user=await pdb.get_user(db,user_id)
    has_permissions=await check_permissions(user)
    if has_permissions['status']:
        pnl=await get_three_month_pnl(user)
        text=msg.get_user_text(user,pnl,False)
    else:
        text=msg.get_user_text(user,{},False)
        text+=msg.get_permission_text(has_permissions)
    await call.message.edit_text(text,reply_markup=kbrd.user_menu(user))



@router.callback_query(lambda call: call.data=='admin_settings')
async def admin_settings_callback(call:CallbackQuery, redis_client:RedisClient):
    global_settings=(await redis_client.get_all_trade_settings()).to_dict()
    text=msg.get_global_settings_text(global_settings)
    await call.message.edit_text(text=text,reply_markup=kbrd.admin_settings_menu())
