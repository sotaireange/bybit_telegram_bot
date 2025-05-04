import logging


from aiogram.types import CallbackQuery,Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter


from app.telegram import keyboards
from app.telegram.fsm import Main,Set
from app.telegram.handlers.user.nav_handler import main_menu_callback
from app.telegram.utils.messages import msg
from app.telegram.utils.limit import Limit





from . import setting_router as router


logger = logging.getLogger('telegram')


@router.callback_query(lambda call: call.data in ['leverage','size','balance','take_profit'])
async def set_state(call: CallbackQuery, state: FSMContext):
    data:str=call.data
    await state.set_state(f'Set:{data.upper()}')
    limit = getattr(Limit, data.upper(), (0, 0))
    text=msg('input_setting',data,limit[0],limit[1])
    await call.message.edit_text(text=text,reply_markup=keyboards.cancel_menu())

@router.callback_query(lambda call: call.data in ['api','secret'])
async def set_api_state(call: CallbackQuery, state: FSMContext):
    data:str=call.data
    await state.set_state(f'Set:{data.upper()}')
    text=msg('api_info') if data=='api' else msg('secret_info')
    await call.message.edit_text(text=text,reply_markup=keyboards.cancel_menu())



@router.message(StateFilter(Set.SECRET,Set.API))
async def update_api(message: Message, state: FSMContext):
    value=message.text
    state_text=(await state.get_state()).split(':')[1].lower()
    text=msg('input_success',state_text,value)
    await message.answer(text=text,reply_markup=keyboards.stock_menu())
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

