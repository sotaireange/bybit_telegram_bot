import logging
from aiogram.enums import ParseMode
from sqlalchemy.ext.asyncio import AsyncSession

from aiogram.types import CallbackQuery,Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter


from app.telegram import keyboards
from app.telegram.fsm import Main,Set
from app.telegram.handlers.user.nav_handler import main_menu_callback
from app.telegram.utils.messages import msg
from app.telegram.utils.limit import Limit


from app.db.models import Notification,UserAPI
from app.db.services import postgres_db as pdb
from app.common.config import settings

from . import setting_router as router


logger = logging.getLogger('telegram')


@router.callback_query(lambda call: call.data.split('_')[0]=='switch')
async def switch_api_key(call: CallbackQuery, state: FSMContext,db:AsyncSession):
    name=call.data.split('_')[1]
    if name=='': return
    api=(await pdb.get_user_one_api(db=db, user_id=call.from_user.id,name=name))
    value= False if api.run else True
    await pdb.update_user_api(db=db, user_id=call.from_user.id,name=name,run=value)
    user= await pdb.get_user(db=db,user_id=call.from_user.id)
    text=msg.get_stock_text(user)
    await call.message.edit_text(text,reply_markup=keyboards.stock_menu(run=value,name=api.name),parse_mode=ParseMode.HTML)

@router.callback_query(lambda call: call.data.split('_')[0]=='delete')
async def delete_api_key(call: CallbackQuery, state: FSMContext,db:AsyncSession):
    name=call.data.split('_')[1]
    try:
        await pdb.delete_user_api(db=db, user_id=call.from_user.id,name=name)
    except:
        logger.error(f"Failed delete api key {name}")
    apis=await pdb.get_user_apis(db=db,user_id=call.from_user.id)
    text=msg.get_user_apis_text(apis)
    await call.message.edit_text(text=text,reply_markup=keyboards.new_stock_menu(apis))

@router.callback_query(lambda call: call.data in [])#['leverage','size','balance','take_profit'])
async def set_state(call: CallbackQuery, state: FSMContext):
    data:str=call.data
    await state.set_state(f'Set:{data.upper()}')
    limit = getattr(Limit, data.upper(), (0, 0))
    text=msg('input_setting',data,limit[0],limit[1])
    await call.message.edit_text(text=text,reply_markup=keyboards.cancel_menu())

@router.callback_query(lambda call: call.data in ['main_open','main_close','hedge_open','hedge_close'])
async def change_notification_level(call: CallbackQuery, state: FSMContext,db:AsyncSession):
    notification=await pdb.update_notification(db,call.from_user.id,call.data)
    text=msg.get_notification_text(notification)
    await call.message.edit_text(text=text,reply_markup=keyboards.notification_menu(notification))


@router.callback_query(lambda call: call.data=='new_api_key')
async def set_name_api_state(call: CallbackQuery, state: FSMContext):
    await state.set_state(f'Set:NAME')
    text=msg('api_name')
    await call.message.edit_text(text=text,reply_markup=keyboards.cancel_menu(),parse_mode=ParseMode.HTML)

@router.callback_query(lambda call: call.data.split('_')[0] in ['api','secret'])
async def set_api_state(call: CallbackQuery, state: FSMContext):
    data,name=call.data.split('_')
    await state.set_state(f'Set:{data.upper()}')
    if name not in ['',None]:
        await state.set_data({'name':name})
    text=msg('api_info') if data=='api' else msg('secret_info')
    await call.message.edit_text(text=text,reply_markup=keyboards.cancel_menu(),parse_mode=ParseMode.HTML)



@router.message(StateFilter(Set.SECRET,Set.API,Set.NAME))
async def update_api(message: Message, state: FSMContext,api:UserAPI):
    value=message.text
    state_text=(await state.get_state()).split(':')[1].lower()
    text=msg('input_success',state_text,value)
    await message.answer(text=text,reply_markup=keyboards.stock_menu(run=api.run,name=api.name))
    await message.bot.delete_message(chat_id=message.chat.id,message_id=message.message_id)
    await message.bot.delete_message(chat_id=message.chat.id,message_id=message.message_id-1)



@router.message(StateFilter(Set))
async def update_data(message: Message, state: FSMContext):
    value=float(message.text)
    state_text=(await state.get_state()).split(':')[1].lower()

    await state.set_state(Main.UNRUN)
    text=msg('input_success',state_text,value)
    await message.answer(text=text,reply_markup=keyboards.settings_menu())
    await message.bot.delete_message(chat_id=message.chat.id,message_id=message.message_id)
    await message.bot.delete_message(chat_id=message.chat.id,message_id=message.message_id-1)



# @router.callback_query(lambda call: call.data=='cancel')
# async def cancel(call: CallbackQuery, state: FSMContext):
#     await state.set_state(Main.UNRUN)
#     await call.message.edit_text(Msg.SETTINGS, reply_markup=keyboards.settings_menu())

