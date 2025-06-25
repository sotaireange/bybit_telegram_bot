import hashlib
import random
import json
import logging
from typing import Dict
from aiohttp import web

from urllib.parse import parse_qs
from aiogram import Bot


from app.db.database import r
from app.common.config import settings

logger = logging.getLogger('payment')


def generate_sign(order_amount: float, order_id: int) -> str:
    sign_string = f"{settings.FK_ID}:{order_amount}:{settings.FK_SECRET_1}:{settings.FK_CURRENCY}:{order_id}"
    sign = hashlib.md5(sign_string.encode('utf-8')).hexdigest()
    return sign

def get_payment_url_fk(order_amount: float, order_id: int, user_id: int):
    sign = generate_sign(order_amount, order_id)
    url = f"https://pay.freekassa.ru/?m={settings.FK_ID}&oa={order_amount}&o={order_id}&s={sign}&currency={settings.FK_CURRENCY}&us_login={user_id}&lang=ru"
    return url


async def handle_success_payment_fk(bot:Bot,data_dict:Dict):
    logger.info(f'SUCCES PAYMENT {data_dict}')


async def handle_payment_fk(request: web.Request) -> web.Response:
    try:
        data = await request.post()
        data_dict = dict(data)

        logger.info(f"Payment webhook data received: {json.dumps(data_dict, indent=2)}")

        if not data_dict:
            logger.warning("Payment webhook received empty form data")
            return web.Response(text="ERROR", status=400)


        await r.set('last_payment_fk_webhook_data', json.dumps(data_dict))

        bot: Bot = request.app['bot']
        await handle_success_payment_fk(bot,data_dict)
        return web.Response(text="YES", status=200)


    except Exception as e:
        logger.error(f"Unexpected error processing payment webhook: {str(e)}", exc_info=True)
        return web.Response(text="ERROR", status=500)