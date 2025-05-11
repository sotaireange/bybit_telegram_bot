import asyncio
from aiogram.types import Message
from aiogram import Bot
from datetime import datetime


from app.db.models import TelegramMessage
from app.telegram.utils.messages import msg



async def send_notification(bot:Bot, telegram_msg: TelegramMessage):
    user_id=telegram_msg.user_id
    text=msg.get_stock_message(telegram_msg)
    text='ТЕСТ'
    await bot.send_message(chat_id=user_id,text=text,parse_mode='HTML')

