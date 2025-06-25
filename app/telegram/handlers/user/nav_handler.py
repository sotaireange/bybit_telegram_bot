import logging

from aiogram.enums import ParseMode
from aiogram import Bot

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message,ChatMemberUpdated,BotCommand
from aiogram.filters import CommandStart,Command
from sqlalchemy.ext.asyncio import AsyncSession


from app.db.services import postgres_db as pdb
from app.db.services import RedisClient
from app.db.models import User,Run

from app.telegram import keyboards
from app.telegram.fsm import Main
from . import navigate_router as router
from app.telegram.utils.messages import msg
from app.telegram.utils.stock_helper import check_permissions, get_user_positions,close_all_order_user
from ...utils.pnl_helper import get_user_pnl

logger = logging.getLogger('aiogram')
#TODO: сделать дубликат /menu /position /exit
#прописывает /exit там всплывает уведомление - столько-то примерно будет минус, уверены? и кнопка Да Нет




@router.startup()
async def setup_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="menu", description="📋 Главное меню"),
        BotCommand(command="positions", description="📊 Мои позиции"),
        BotCommand(command="total_exit",description="Выход из всех позиций! "),
    ]
    await bot.set_my_commands(commands)

@router.message(CommandStart(),flags={'create':True})
async def start_message(message: Message,redis_client: RedisClient,user: User):
    flag=await redis_client.get_is_run(int(message.from_user.id))
    await message.answer(msg('welcome'),reply_markup=keyboards.main_menu(flag))


@router.callback_query(lambda call: call.data=='main_menu')
async def main_menu_callback(call: CallbackQuery, state: FSMContext,redis_client: RedisClient,user:User):
    await state.set_state(Main.UNRUN)
    run=await redis_client.get_is_run(int(call.message.from_user.id))
    text= msg.get_menu_text(user, run)
    try:
        await call.message.edit_text(text,reply_markup=keyboards.main_menu(flag=run))
    except:
        pass

@router.message(Command('menu'))
async def menu_command(message: Message, state: FSMContext, redis_client: RedisClient, user: User):
    run = await redis_client.get_is_run(int(message.from_user.id))
    text = msg.get_menu_text(user, run)
    await message.answer(text, reply_markup=keyboards.main_menu(flag=run))
    await message.delete()

@router.callback_query(lambda call: call.data=='stock_menu')
async def stock_callback(call: CallbackQuery, state: FSMContext,user:User):
    text=msg.get_stock_text(user)
    await call.message.edit_text(text,reply_markup=keyboards.stock_menu(),parse_mode=ParseMode.HTML)


@router.callback_query(lambda call: call.data=='check_api')
async def stock_check_callback(call: CallbackQuery, state: FSMContext,user:User,db:AsyncSession):
    permissions=await check_permissions(user)
    bybit_uid=int(permissions.get('parentUid'))
    if bybit_uid:
        await pdb.update_bybit_uid(db,call.from_user.id,bybit_uid)
    text= msg.get_permission_text(permissions)
    await call.message.edit_text(text,reply_markup=keyboards.stock_menu())


@router.callback_query(lambda call: call.data=='positions')
async def position_callback(call: CallbackQuery,user:User):
    positions=await get_user_positions(user)
    pnl=await get_user_pnl(user)
    text=msg.get_pnl_text(pnl)+msg.get_position_text(positions)
    try:
        await call.message.edit_text(text,reply_markup=keyboards.position_update(),parse_mode='HTML')
    except:
        pass


@router.message(Command('positions'))
async def positions_command(message: Message, user: User):
    positions = await get_user_positions(user)
    pnl = await get_user_pnl(user)
    text = msg.get_pnl_text(pnl) + msg.get_position_text(positions)
    await message.answer(text, reply_markup=keyboards.position_update(), parse_mode='HTML')
    await message.delete()


@router.callback_query(lambda call: call.data=='notification')
async def notification_callback(call: CallbackQuery,db:AsyncSession):
    notification=await pdb.get_notification(db,call.from_user.id)
    text=msg.get_notification_text(notification)
    await call.message.edit_text(text=text,reply_markup=keyboards.notification_menu(notification))


@router.message(Command('exit'))
async def exit_order_handler(message: Message, redis_client: RedisClient, user: User):
    user_id=message.from_user.id
    user=await get_user_positions(user)
    text = msg.get_exit_orders_text(user, pnl)
    await message.answer(text, reply_markup=keyboards.main_menu(flag=run))
    await message.delete()

async def confirm_exit_order_handler(call:CallbackQuery, redis_client: RedisClient,user:User):
    user_id=call.from_user.id
    run = await redis_client.set_is_run(user_id,Run.OFF)

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
