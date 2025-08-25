import logging
import asyncio

from aiogram.enums import ParseMode
from aiogram import Bot

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message,ChatMemberUpdated,BotCommand
from aiogram.filters import CommandStart,Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.config import settings

from app.db.services import postgres_db as pdb
from app.db.services import RedisClient
from app.db.models import User,Run

from app.telegram import keyboards
from app.telegram.fsm import Main
from . import navigate_router as router
from app.telegram.utils.messages import msg
from app.telegram.utils.stock_helper import check_permissions, get_user_positions,close_all_order_user,get_unrealised_pnl_user,check_bybit_uids
from ...utils.pnl_helper import get_user_pnl


logger = logging.getLogger('aiogram')



@router.startup()
async def setup_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🚀 Запустить бота"),
        BotCommand(command="menu", description="📋 Главное меню"),
        BotCommand(command="positions", description="📊 Мои позиции"),
        BotCommand(command="total_exit",description="Выход из всех позиций! ")
    ]
    if settings.TRADING_MODE == 'manually':
        commands.append(
            BotCommand(
                command="signal",
                description="Добавление сигнала (<coin1>,<coin2>_<1>,<0> (1-Long,0-Short)"
            )
        )

    await bot.set_my_commands(commands)

@router.message(CommandStart(),flags={'create':True})
async def start_message(message: Message,redis_client: RedisClient,user: User):
    flag=await redis_client.get_is_run(int(message.from_user.id))
    await message.answer(msg('welcome'),reply_markup=keyboards.main_menu(flag))


@router.callback_query(lambda call: call.data=='main_menu')
async def main_menu_callback(call: CallbackQuery, state: FSMContext,redis_client: RedisClient,user:User):
    await state.set_state(Main.UNRUN)
    run=await redis_client.get_is_run(int(call.from_user.id))
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
async def stock_callback(call: CallbackQuery, state: FSMContext,user:User,db:AsyncSession):
    text=msg.get_stock_text(user)
    if settings.TRADING_MODE=='manually' or (user.id in settings.ADMIN_IDS):
        await call.message.edit_text(text,reply_markup=keyboards.new_stock_menu(user.apis))
    else:
        api=user.pick_api()
        if not api:
            api=await pdb.add_user_api(db=db,user_id=call.from_user.id,name='MAIN')
        await call.message.edit_text(text,reply_markup=keyboards.stock_menu(name=api.name),parse_mode=ParseMode.HTML)


@router.callback_query(lambda call: call.data.split('_')[0]=='stockapi')
async def api_stock_callback(call: CallbackQuery, state:FSMContext,user:User,db:AsyncSession):
    name=call.data.split('_')[1]
    api=user.pick_api(name)
    logger.info(f'Api - {api} name - {name}')
    text=msg.get_api_text(api)
    await call.message.edit_text(text,reply_markup=keyboards.stock_menu(run=api.run,name=api.name),parse_mode=ParseMode.HTML)



# @router.callback_query(lambda call: call.data=='new_api_key')
# async def new_api_key_callback(call: CallbackQuery, state: FSMContext,user:User,db:AsyncSession):
#     text=msg.get_stock_text(user)
#     await call.message.edit_text(text,reply_markup=keyboards.stock_menu(),parse_mode=ParseMode.HTML)



@router.callback_query(lambda call: call.data.split('_')[0]=='check')
async def stock_check_callback(call: CallbackQuery, state: FSMContext,user:User,db:AsyncSession):
    name=call.data.split('_')[1]
    if name=='': return
    permissions=await check_permissions(user,name)
    await check_bybit_uids(db,user,permissions)
    text= msg.get_permission_text(permissions)
    api=(await pdb.get_user_one_api(db,user.id,name=name))
    await call.message.edit_text(text,reply_markup=keyboards.stock_menu(run=api.run,name=api.name))


@router.callback_query(lambda call: call.data.split('_')[0]=='position' or
                                    (call.data=='all_positions' and
                                     not (settings.TRADING_MODE=='manually' or (call.from_user.id in settings.ADMIN_IDS))))
async def position_callback(call: CallbackQuery,user:User):
    api_name=call.data.split('_')[1]
    if api_name=='positions': api_name=None
    positions=await get_user_positions(user,api_name)
    pnl=await get_user_pnl(user,api_name=api_name)
    text=msg.get_pnl_text(pnl)+msg.get_position_text(positions)
    try:
        await call.message.edit_text(text,reply_markup=keyboards.position_update(api_name),parse_mode='HTML')
    except Exception as e:
        logger.error(f'Error when get positions\n {e}')


@router.callback_query(lambda call: call.data=='all_positions')
async def all_position_callback(call: CallbackQuery,user:User):
    text=msg.get_all_positions_text(user.apis)
    await call.message.edit_text(text,reply_markup=keyboards.all_positions(user.apis))



@router.message(Command('positions'))
async def positions_command(message: Message, user: User):
    text=msg.get_all_positions_text(user.apis)
    await message.edit_text(text,reply_markup=keyboards.all_positions(user.apis))


@router.callback_query(lambda call: call.data=='notification')
async def notification_callback(call: CallbackQuery,db:AsyncSession):
    notification=await pdb.get_notification(db,call.from_user.id)
    text=msg.get_notification_text(notification)
    await call.message.edit_text(text=text,reply_markup=keyboards.notification_menu(notification))


@router.message(Command('total_exit'))
async def exit_order_handler(message: Message, redis_client: RedisClient, user: User):
    pnl= await get_unrealised_pnl_user(user)
    text = msg.get_exit_orders_text(pnl)
    await message.answer(text, reply_markup=keyboards.proof_to_exit_orders())
    await message.delete()

@router.callback_query(lambda call: call.data=='yes_exit')
async def confirm_exit_order_handler(call: CallbackQuery,db:AsyncSession,redis_client: RedisClient, user: User):
    user_id=call.from_user.id
    await redis_client.set_is_run(user_id,Run.OFF)
    await asyncio.sleep(5)
    await close_all_order_user(user)
    text= msg.get_menu_text(user, Run.OFF)
    try:
        await call.message.edit_text(text,reply_markup=keyboards.main_menu(flag=Run.OFF))
    except:
        pass


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
