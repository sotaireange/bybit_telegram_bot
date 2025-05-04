import logging


from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message,ChatMemberUpdated
from aiogram.filters import CommandStart
from sqlalchemy.ext.asyncio import AsyncSession


from app.db.services import postgres_db as pdb
from app.db.services import RedisClient
from app.db.models import User,Run

from app.telegram import keyboards
from app.telegram.fsm import Main
from . import navigate_router as router
from app.telegram.utils.messages import msg
from app.telegram.utils.stock_helper import check_permissions,get_three_month_pnl,get_user_positions

logger = logging.getLogger('aiogram')


@router.message(CommandStart(),flags={'create':True})
async def start_message(message: Message,redis_client: RedisClient,user: User):
    flag=await redis_client.get_is_run(int(message.from_user.id))
    await message.answer(msg('welcome'),reply_markup=keyboards.main_menu(flag))


@router.callback_query(lambda call: call.data=='main_menu')
async def main_menu_callback(call: CallbackQuery, state: FSMContext,redis_client: RedisClient,user:User):
    await state.set_state(Main.UNRUN)
    pnl=await get_three_month_pnl(user)
    flag=await redis_client.get_is_run(int(call.message.from_user.id))
    text= msg.get_menu_text(user,pnl,flag)
    await call.message.edit_text(text,reply_markup=keyboards.main_menu(flag=flag))


@router.callback_query(lambda call: call.data=='stock_menu')
async def stock_callback(call: CallbackQuery, state: FSMContext,user:User):
    text=msg.get_stock_text(user)
    await call.message.edit_text(text,reply_markup=keyboards.stock_menu())


@router.callback_query(lambda call: call.data=='check_api')
async def stock_check_callback(call: CallbackQuery, state: FSMContext,user:User,db:AsyncSession):
    permissions=await check_permissions(user)
    bybit_uid=int(permissions['parentUid'])
    await pdb.update_bybit_uid(db,call.from_user.id,bybit_uid)
    text= msg.get_permission_text(permissions)
    await call.message.edit_text(text,reply_markup=keyboards.stock_menu())


@router.callback_query(lambda call: call.data=='positions')
async def position_callback(call: CallbackQuery,user:User):
    positions=await get_user_positions(user)
    text=msg.get_position_text(positions)
    await call.message.edit_text(text,reply_markup=keyboards.cancel_menu(),parse_mode='HTML')



@router.my_chat_member()
async def check_blocked_handler(message: ChatMemberUpdated, db:AsyncSession, redis_client:RedisClient):
    if message.chat.type == 'private':
        user_id=int(message.from_user.id)
        if message.new_chat_member.status == "kicked":
            await redis_client.set_is_run(user_id, Run.OFF)
            await pdb.update_user_fields(db,user_id,{'is_banned': True})
        elif message.new_chat_member.status == "member":
            await pdb.update_user_fields(db,user_id,{'is_banned': False})


# @router.callback_query(lambda call: call.data=='settings')
# async def setting_callback(call: CallbackQuery,state: FSMContext,user:User):
#     text=get_settings_text(user)
#     await call.message.edit_text(text,reply_markup=keyboards.settings_menu())
