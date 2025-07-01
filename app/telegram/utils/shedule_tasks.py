import asyncio
from typing import Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from faststream.redis import RedisBroker

import logging
from datetime import datetime,timedelta,timezone
from app.common.loggers import setup_logging
from sqlalchemy.ext.asyncio import async_sessionmaker,AsyncSession
from app.telegram.utils.pnl_helper import get_all_user_pnl
from app.db.models import Run,TelegramMessage,NotificationType,User,Payment
from app.worker.broker import publish_telegram_message
from app.db.services.redis_db import RedisClient
from app.db.services import postgres_db as pdb

logger = logging.getLogger('payment')
async def create_and_send_notification(broker:RedisBroker,redis_client:RedisClient,db:AsyncSession,pnl_users:Dict[User,float]):
    for user,pnl in pnl_users.items():
        tg_msg=TelegramMessage(user_id=user.id,type=NotificationType.PAYMENT,data=pnl)
        if pnl>0:
            logger.info(f'Send notification to {user.id} {user.username}')
            is_run=await redis_client.get_is_run(user.id)
            if is_run==Run.ACTIVE:
                await redis_client.set_is_run(user.id,Run.HEDGE_SUB)
            amount=round(pnl/2,2)
            await Payment.update_payment(db,user.id,amount=amount)
            await publish_telegram_message(broker,tg_msg)
        elif pnl<0:
            logger.info(f'pnl<0 send notification {user.id} {user.username}')
            await publish_telegram_message(broker,tg_msg)
        if pnl<=0:
            await pdb.extend_subscription(db,user.id,days=1)

async def daily_task(broker:RedisBroker,redis_client:RedisClient,session:async_sessionmaker):
    async with session() as db:
        users=await pdb.get_all_users(db)
    pnl_users=await get_all_user_pnl(users)
    async with session() as db:
        await create_and_send_notification(broker,redis_client,db,pnl_users)



def create_and_start_scheduler(broker:RedisBroker,redis_client:RedisClient,session:async_sessionmaker) -> AsyncIOScheduler:
    msk_tz=timezone(timedelta(hours=3))
    scheduler = AsyncIOScheduler(timezone=msk_tz)
    scheduler.add_job(
        daily_task,
        trigger=CronTrigger(hour=18,minute=0, timezone=msk_tz),
        args=[broker,redis_client,session],
        id='job_everyday',
        name='Every day job(Subs and PNL)',
        replace_existing=True
    )
    scheduler.start()
    logger.info(f"Scheduler started")
    return scheduler
