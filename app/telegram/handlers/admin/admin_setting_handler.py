import logging

from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter

from app.telegram.keyboards import admin as kbrd
from app.telegram.fsm import Main,AdminSet


from .admin_messages import msg


from . import router_setting as router

logger = logging.getLogger('aiogram')




@router.callback_query(lambda call: call.data in ['volume_long','volume_short',
                                                  'long_percentage','short_percentage',
                                                  'leverage','size','balance','take_profit',
                                                  'hedge_percentage'])
async def set_state(call: CallbackQuery, state: FSMContext):
    data:str=call.data
    await state.set_state(f'AdminSet:{data.upper()}')
    text=msg('input_setting',data)
    await call.message.edit_text(text=text,reply_markup=kbrd.admin_cancel_menu())



@router.message(StateFilter(AdminSet))
async def update_data(message: Message, state: FSMContext):
    value=float(message.text)
    state_text=(await state.get_state()).split(':')[1].lower()
    await state.set_state(Main.UNRUN)
    text=msg('input_succes',state_text,value)
    await message.answer(text=text,reply_markup=kbrd.admin_settings_menu())
    await message.bot.delete_message(chat_id=message.chat.id,message_id=message.message_id)
    await message.bot.delete_message(chat_id=message.chat.id,message_id=message.message_id-1)