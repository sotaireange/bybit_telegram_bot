import asyncio
from aiogram.types import Message
from datetime import datetime


async def send_notification(info,bybit,reverse,message: Message,indicator):
    side=info['side']
    reverse="Реверс" if reverse else ""
    amount=round(float(info['amount']),2)
    coin=info['coin']
    price=float(info['price'])
    side='🟢LONG' if side=='Buy' else '🔴SHORT'
    time_now=datetime.now().strftime('%d.%m.%Y %H:%M:%S')
    stock_text='Bybit' if bybit else 'Binance'
    coin_text= f'<a href="https://ru.tradingview.com/chart/XwbHZqWY/?symbol={stock_text.upper()}%3A{coin}.P">{coin}</a>'
    if indicator=='aroon' and not reverse:
        text_source=info.get('source','')
    else:
        text_source=""

    text=(f'{side} {indicator} {text_source} {reverse}\n'
          f'🪙Монета {coin_text}\n'
          f'🏦Биржа {stock_text}\n'
          f'📈Цена: {price}$\n'
          f'💰Сумма: {amount}$\n'
          f'🕙Время {time_now}\n')
    await message.answer(text=text,parse_mode='HTML')


async def send_notification_short(order,bybit,message: Message):
    stopPrice=order['stopPrice']
    coin=order['symbol']
    time_now=datetime.now().strftime('%d.%m.%Y %H:%M:%S')

    stock_text='Bybit' if bybit else 'Binance'

    text=(f'Перенос стопа на профит\n'
          f'🪙Монета {coin}\n'
          f'🏦Биржа {stock_text}\n'
          f'📈Цена стопа: {stopPrice}$\n'
          f'🕙Время: {time_now}\n')

    await message.answer(text=text)


async def error_notification(message:Message, error,coin):
    text=f'Возникла ошибка по монетке {coin}\n{error}'
    await message.answer(text=text)

async def not_balance_notification(message:Message):
    text=(f'📉Недостаточный баланс\n')
    await message.answer(text=text)