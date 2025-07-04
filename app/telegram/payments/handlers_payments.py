from typing import Dict
from aiogram import Bot
import json
import logging

from app.db.models import PaymentType,PaymentSucces,Payment,PaymentStatus
from app.db.database import AsyncSessionLocal,r
from app.db.services import postgres_db
from app.db.services.redis_db import RedisClient

from app.telegram.utils.messages import msg

from app.telegram.payments.utils import change_run

logger = logging.getLogger('payment')




async def handle_success_payment(bot:Bot, data:PaymentSucces,redis_client:RedisClient):
    try:

        payment_order_data= data.extract_data()

        async with AsyncSessionLocal() as session:
            await postgres_db.extend_subscription_due_time(session,
                                                           user_id=payment_order_data.user_id,
                                                           time=payment_order_data.time)
            payment=await Payment.update_payment(session,user_id=payment_order_data.user_id,
                                                status=PaymentStatus.SUCCESS,type=data.type)

        if payment:
            await change_run(redis_client,user_id=payment_order_data.user_id)
            text=msg.get_succes_payment_text(payment)
            await bot.send_message(payment_order_data.user_id,text=text)
    except Exception as e:
        logger.error(f'Error {e}')
        raise e