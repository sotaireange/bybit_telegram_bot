import asyncio
from aiogram.types import Message
from aiogram import Bot
from aiogram.exceptions import TelegramForbiddenError
from datetime import datetime


from app.db.models import TelegramMessage,Notification,PositionType,NotificationType
from app.telegram.utils.messages import msg
from app.db.services import postgres_db as pdb
from app.db.database import AsyncSessionLocal

def get_notification_field(position_type: PositionType, notification_type: NotificationType) -> str:

    if position_type == PositionType.MAIN and notification_type == NotificationType.POSITION_OPEN:
        return 'main_open'
    elif position_type == PositionType.MAIN and notification_type == NotificationType.POSITION_CLOSE:
        return 'main_close'
    elif position_type == PositionType.HEDGE and notification_type == NotificationType.POSITION_OPEN:
        return 'hedge_open'
    elif position_type == PositionType.HEDGE and notification_type == NotificationType.POSITION_CLOSE:
        return 'hedge_close'
    else:
        return 'main_open'


async def send_notification(bot:Bot, telegram_msg: TelegramMessage):
    user_id=telegram_msg.user_id
    async with AsyncSessionLocal() as session:
        notification=await pdb.get_notification(session,user_id)
    if NotificationType in [NotificationType.POSITION_OPEN, NotificationType.POSITION_CLOSE]:
        field_name = get_notification_field(telegram_msg.data.position_type, telegram_msg.type)
        if not getattr(notification, field_name):
            return
    if telegram_msg.type == NotificationType.ERROR:
        text=msg('error_when_trading')
    elif telegram_msg.type == NotificationType.PAYMENT:
        text=msg.get_payment_text(telegram_msg.data)
    else:
        text=msg.send_order_notification(telegram_msg)
    try:
        await bot.send_message(chat_id=user_id,text=text,parse_mode='HTML')
    except TelegramForbiddenError:
        async with AsyncSessionLocal() as db:
            await pdb.update_user_fields(db,user_id,{'is_banned': True})


