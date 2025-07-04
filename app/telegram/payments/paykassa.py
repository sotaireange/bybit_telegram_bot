import json
import logging
from typing import Dict
from aiohttp import web,ClientSession
import urllib
from urllib.parse import parse_qs
from aiogram import Bot


from app.db.database import r
from app.db.services.redis_db import RedisClient
from app.db.models import PaymentSucces,PaymentType
from app.common.config import settings

from app.telegram.payments.handlers_payments import handle_success_payment

logger = logging.getLogger('payment')


async def make_request(params:Dict):
    url='https://paykassa.app/sci/0.4/index.php'
    fields={'sci_id':settings.SHOP_PK,
            'sci_key': settings.SHOP_PASSWORD_PK}

    fields.update(params)

    async with ClientSession() as session:
        encoded_fields=urllib.parse.urlencode(fields)
        try:
            async with session.post(url,
                                    data=encoded_fields,
                                    headers={'Content-Type': 'application/x-www-form-urlencoded'}
                                    ) as response:
                response_text = await response.text()
                return json.loads(response_text)
        except Exception as e:
            logger.error(f"PayKassa API request error: {e}")
            return {'error':True,
                    'msg':str(e)}

async def create_payment_order_pk(order_amount: float, order_id: str):
    params={'func':'sci_create_order',
            'order_id': order_id,
            'currency': 'USDT',
            'amount': order_amount,
            'system': 30,
            'comment':'Оплата подписки в Телеграм боте',

    }
    return await make_request(params)


async def get_payment_url_pk(amount: float, order_id: str) -> str | None:
    result = await create_payment_order_pk(amount,order_id)
    if result.get('error'):
        logger.error(f"Error creating payment: {result['error']}")
        return None

    if result.get('data') and result.get('data',{}).get('url'):
        return result['data']['url']

    logger.error(f"No payment URL in response: {result}")
    return None




async def check_payment_status(private_hash: str) -> dict:
    params = {
        'func': 'sci_confirm_order',
        'private_hash': private_hash
    }

    result = await make_request(params)
    logger.debug(f"Payment Succes status check: {private_hash}")
    return result

def extract_user_id_from_order(order_id: str) -> int | None:
    try:
        parts = order_id.split('-')
        user_part=parts[0].split('_')
        if len(user_part) >= 2 and user_part[0] == 'user':
            return int(user_part[1])
    except Exception as e:
        logger.error(f'Error {e}')
        pass
    return None


async def validate_payment_notification(data: dict) -> bool:
    required_fields = ['private_hash', 'order_id', 'amount', 'currency']
    for field in required_fields:
        if field not in data:
            logger.warning(f"Missing required field in payment notification: {field}")
            return False

    return True



async def handle_payment_pk(request: web.Request) -> web.Response:
    try:
        data = await request.post()
        data_dict = dict(data)

        logger.debug(f"Payment webhook data received: {json.dumps(data_dict, indent=2)}")

        if not data_dict:
            logger.warning("Payment webhook received empty form data")
            return web.Response(text="ERROR", status=400)

        await r.set('last_payment_paykassa_webhook_data', json.dumps(data_dict))

        bot: Bot = request.app['bot']
        redis_client: RedisClient=request.app['redis_client']
        order_id=await handle_success_pk(bot, data_dict,redis_client)

        return web.Response(text=f"{order_id}|success", status=200)

    except Exception as e:
        logger.error(f"Error processing payment notification: {e}")
        return web.Response(text="ERROR", status=500)


async def handle_success_pk(bot: Bot, payment_data: dict,redis_client:RedisClient) -> str:
    try:
        private_hash = payment_data.get('private_hash')

        logger.debug(f"Processing successful payment: Order {private_hash}")

        payment_status = await check_payment_status(private_hash)

        if payment_status.get('data', {}).get('status') != 'false':
            payment_success_data = payment_status.get('data')
            order_id = payment_success_data.get('order_id')
            amount = float(payment_success_data.get('amount',0))
            user_id = extract_user_id_from_order(order_id)
            if user_id:
                payment_success=PaymentSucces(order_id=order_id, amount=amount,type=PaymentType.PK)
                await handle_success_payment(bot, payment_success,redis_client)

            logger.debug(f"Payment {order_id} processed successfully")
            return order_id
        else:
            logger.warning(f"Payment {payment_data} status check failed: {payment_status}")

    except Exception as e:
        logger.error(f"Error handling successful payment: {e}")



