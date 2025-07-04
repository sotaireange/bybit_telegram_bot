import logging
import asyncio
from datetime import datetime,timezone

from sqlalchemy.ext.asyncio import AsyncSession
from faststream.redis import RedisBroker

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery


from app.worker.broker import publish_task

from app.db.models import User,Run,Task,TaskMessage,TaskType
from app.db.services import RedisClient, postgres_db as pdb

from app.telegram import keyboards
from app.telegram.utils.stock_helper import check_permissions
from app.telegram.utils.messages import msg
from app.telegram.utils.datetime_helper import sub_is_over
from app.telegram.utils.stock_helper import check_bybit_uids


router=Router(name='run')


logger=logging.getLogger('aiogram')




@router.callback_query(lambda call: call.data=="run")
async def run(call: CallbackQuery, state: FSMContext,redis_client:RedisClient,user:User,db:AsyncSession,broker:RedisBroker):
    if not user.api or not user.secret:
        text=msg('lost_api_secret')
        await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))
        return

    status=await check_permissions(user)
    user_id=call.from_user.id
    await check_bybit_uids(db,user)
    user=await pdb.get_user(db,user_id)
    if not status.get('status',0):
        text=msg.get_permission_text(status)
        await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))
        return
    await redis_client.set_is_run(user_id,Run.OFF)


    if sub_is_over(user):
        text=msg('sub_is_over')
        await call.message.edit_text(text=text,reply_markup=keyboards.subs_menu())
        return
    if user.bybit_uid is None:
        text=msg('bybit_uid_is_bad')
        await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))
        return

    if not user.bybit_sub_account_uid:
        text=msg('get_bybit_uid_error')('')
        await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))
        return

    text= msg.get_menu_text(user, Run.ACTIVE)
    await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.ACTIVE))

    await Task.get_user_task_with_wait(db,user_id)

    task=await Task.create_task(db,user_id=user_id,type=TaskType.MAIN)
    task_msg=TaskMessage(task_id=task.id,user_id=user_id,task_type=TaskType.MAIN)
    await redis_client.set_is_run(user_id,Run.ACTIVE)
    await publish_task(broker,task_msg)


@router.callback_query(lambda call: call.data=="hedge")
async def unrun(call: CallbackQuery, state: FSMContext,redis_client:RedisClient,user:User,db:AsyncSession,broker:RedisBroker):
    if not user.api or not user.secret:
        text=msg('lost_api_secret')
        await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))
        return

    status=await check_permissions(user)
    user_id=call.from_user.id
    await check_bybit_uids(db,user)
    user=await pdb.get_user(db,user_id)
    if not status.get('status',0):
        text=msg.get_permission_text(status)
        await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))
        return
    text= msg.get_menu_text(user, Run.HEDGE)

    if user.bybit_uid is None:
        text=msg('bybit_uid_is_bad')
        await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))
        return

    if not user.bybit_sub_account_uid:
        text=msg('get_bybit_uid_error')('')
        await call.message.edit_text(text=text,reply_markup=keyboards.main_menu(Run.OFF))
        return
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





