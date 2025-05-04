from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
import asyncio
from app.telegram import keyboards

from app.telegram.fsm.run import Main
import logging

router=Router(name='run')


@router.callback_query(lambda call: call.data=="run")
async def run(call: CallbackQuery, state: FSMContext):
    #TODO: МБ ПРОВЕРКА ДЛЯ API SECRET(Не запускать пока не будет доступов)
    await call.message.edit_text(text='Бот работает',reply_markup=keyboards.main_menu(False))
    await asyncio.sleep(10)
    await state.update_data({'run':1})
    await state.set_state(Main.RUN)
    logging.info('Бот включился')




@router.callback_query(lambda call: call.data=="unrun")
async def unrun(call: CallbackQuery, state: FSMContext):
    await state.set_state(Main.UNRUN)
    await state.update_data({'run': 0})
    logging.info('Бот отключился')





