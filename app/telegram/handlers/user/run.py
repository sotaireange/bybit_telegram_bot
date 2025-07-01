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






@router.callback_query(lambda call: call.data=="run")
async def run(call: CallbackQuery, state: FSMContext,redis_client:RedisClient,user:User,db:AsyncSession,broker:RedisBroker):
    status=await check_permissions(user)
    user_id=call.from_user.id
    if not status.get('status',0):
        text=msg.get_permission_text(status)
        await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))
    await redis_client.set_is_run(user_id,Run.OFF)
    text= msg.get_menu_text(user, Run.ACTIVE)
    await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.ACTIVE))

    await Task.get_user_task_with_wait(db,user_id)

    task=await Task.create_task(db,user_id=user_id,type=TaskType.MAIN)
    task_msg=TaskMessage(task_id=task.id,user_id=user_id,task_type=TaskType.MAIN)
    await redis_client.set_is_run(user_id,Run.ACTIVE)
    await publish_task(broker,task_msg)


@router.callback_query(lambda call: call.data=="hedge")
async def unrun(call: CallbackQuery, state: FSMContext,redis_client:RedisClient,user:User,db:AsyncSession,broker:RedisBroker):
    status=await check_permissions(user)
    user_id=call.from_user.id
    if not status.get('status',0):
        text=msg.get_permission_text(status)
        await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))
    text= msg.get_menu_text(user, Run.HEDGE)
    await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.HEDGE))

    task=await Task.get_user_task(db,user_id)

    await redis_client.set_is_run(user_id,Run.HEDGE)

    if not task:
        task=await Task.create_task(db,user_id=user_id,type=TaskType.HEDGE)
        task_msg=TaskMessage(task_id=task.id,user_id=user_id,task_type=TaskType.HEDGE)
        await publish_task(broker,task_msg)
    else:
        task=task[0]
        if isinstance(task,Task):
            await Task.update(db,task_id=task.id,type=TaskType.HEDGE)
            logger.debug('task.type success changed')
        else:
            logger.error("Task Not found, Maybe fix Task.get_user_task()")

@router.callback_query(lambda call: call.data=="unrun")
async def unrun(call: CallbackQuery, state: FSMContext,redis_client:RedisClient,user:User,db:AsyncSession,broker:RedisBroker):
    user_id=int(call.from_user.id)
    await redis_client.set_is_run(user_id,Run.OFF)
    text=msg('user_when_stop')
    text_menu= msg.get_menu_text(user, Run.OFF)
    text=text+text_menu
    await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))

    await Task.get_user_task_with_wait(db,user_id)





