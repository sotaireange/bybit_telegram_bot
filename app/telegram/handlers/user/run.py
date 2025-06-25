import logging
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from faststream.redis import RedisBroker


from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message


from app.worker.broker import publish_task

from app.db.models import User,Run,Task,TaskMessage,TaskType
from app.db.services import RedisClient,postgres_db as pdb

from app.telegram import keyboards
from app.telegram.utils.stock_helper import check_permissions
from app.telegram.utils.messages import msg
import logging
from aiogram.filters import Command

router=Router(name='run')


logger=logging.getLogger('aiogram')

#TODO: Сделать проверку на api/secret. Следом сделать проверку на подписку. Поставить 3 уровня Active, Hedge, OFF/
# Так же нужно перенести профит в positions.

#TODO: Запускаем полностью бота RUN , отключчаем покупку новых позиций Hedge, отключаем полностью бота Stop, Отключаем и выходим Exit


#TODO: Можно сделать так: перед запуском проверяем - есть ли активные задачи, если есть - запускаем новую, если нет - так далее, после unrun - полностью отрубаем задачу(ждем 10-20 секунд)

@router.callback_query(lambda call: call.data=="run")
async def run(call: CallbackQuery, state: FSMContext,redis_client:RedisClient,user:User,db:AsyncSession,broker:RedisBroker):
    status=await check_permissions(user)
    user_id=call.from_user.id
    if not status.get('status',0):
        text=msg.get_permission_text(status)
        await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))
    await asyncio.sleep(5)
    await redis_client.set_is_run(user_id,Run.OFF)
    text= msg.get_menu_text(user, Run.ACTIVE)
    await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.ACTIVE))

    await asyncio.sleep(3)
    task=await Task.create_task(db,user_id=user_id)
    task_msg=TaskMessage(task_id=task.id,user_id=user_id,task_type=TaskType.MAIN)
    await redis_client.set_is_run(user_id,Run.ACTIVE)
    logger.info(f'ALARM! {user_id} START BOT ')
    await publish_task(broker,task_msg)


@router.callback_query(lambda call: call.data=="hedge")
async def unrun(call: CallbackQuery, state: FSMContext,redis_client:RedisClient,user:User,db:AsyncSession,broker:RedisBroker):
    status=await check_permissions(user)
    user_id=call.from_user.id
    if not status.get('status',0):
        text=msg.get_permission_text(status)
        await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))
    await asyncio.sleep(5)
    await redis_client.set_is_run(user_id,Run.OFF)
    text= msg.get_menu_text(user, Run.HEDGE)
    await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.HEDGE))
    await asyncio.sleep(3)
    task=await Task.create_task(db,user_id=user_id)
    task_msg=TaskMessage(task_id=task.id,user_id=user_id,task_type=TaskType.HEDGE)
    await redis_client.set_is_run(user_id,Run.HEDGE)

    await publish_task(broker,task_msg)

@router.callback_query(lambda call: call.data=="unrun")
async def unrun(call: CallbackQuery, state: FSMContext,redis_client:RedisClient,user:User,db:AsyncSession,broker:RedisBroker):
    user_id=int(call.from_user.id)
    await redis_client.set_is_run(user_id,Run.OFF)
    text=msg('user_when_stop')
    text_menu= msg.get_menu_text(user, Run.OFF)
    text=text+text_menu
    logger.info(f'ALARM! {user_id} STOP BOT!!!! ')

    await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))





