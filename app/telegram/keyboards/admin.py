from typing import Sequence
from app.db.models import User,UserAPI

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.common.config import settings


def admin_menu():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Список пользователей",callback_data="users"))
    markup.row(InlineKeyboardButton(text="Изменить глобальные настройки",callback_data="admin_settings"))
    markup.row(InlineKeyboardButton(text="Полный стоп",callback_data="stop_total"))
    return markup.as_markup()


def all_users_menu(users:Sequence[User]):
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Назад",callback_data="admin_menu"))
    for user in users:
        markup.row(InlineKeyboardButton(text=f'{user.username} - {user.id}',callback_data=f"user:{user.id}"))
    return markup.as_markup()

def user_menu(user:User):
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text=f'Дать подписку',callback_data=f"user_sub:{user.id}"))
    markup.row(InlineKeyboardButton(text=f'Отменить подписку',callback_data=f"user_unsub:{user.id}"))
    markup.row(InlineKeyboardButton(text="Список ордеров",callback_data=f"user_orders:{user.id}"))
    markup.row(InlineKeyboardButton(text=f'Остановить всю торговлю',callback_data=f"user_stop:{user.id}"))
    markup.row(InlineKeyboardButton(text=f'Закрыть все сделки',callback_data=f"user_exit:{user.id}"))
    markup.row(InlineKeyboardButton(text="Назад",callback_data="admin_menu"))
    return markup.as_markup()


def user_api_menu(user:User):
    markup = InlineKeyboardMarkup()
    for api in user.apis:
        markup.row(InlineKeyboardButton(text=f"Позиция {api.name}",callback_data=f"user_position:{user.id}:{api.name}"))
    markup.row(InlineKeyboardButton(text="Назад",callback_data="admin_menu"))
    return markup.as_markup()


def are_you_sure():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(text='Да',callback_data="yes_stop"))
    markup.row(InlineKeyboardButton(text='Нет',callback_data="admin_menu"))
    return markup.as_markup()


from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

def admin_settings_menu():

    markup = InlineKeyboardBuilder()
    trading_mode=settings.TRADING_MODE
    all_buttons = [
        ('Объем Лонг', 'Объем Лонг', 'volume_long', ('auto', 'manually')),
        ('Объем Шорт', 'Объем Шорт', 'volume_short', ('auto',)),
        ('Процент Лонг', 'Процент Лонга', 'long_percentage', ('auto', 'manually')),
        ('Процент Шорт', 'Процент Шорта', 'short_percentage', ('auto',)),
        ('Процент баланса от общего', 'Процент баланса от общего', 'size', ('auto', 'manually')),
        ('Максимальный баланс', 'Максимальный баланс', 'balance', ('auto', 'manually')),
        ('Процент прибыли(Take Profit)', 'Тейк Профит Безубытка', 'take_profit', ('auto', 'manually')),
        ('Процент Хеджа Long', 'Процент Хеджа Long', 'hedge_percentage_long', ('auto',)),
        ('Процент Хеджа Short', 'Процент Хеджа Short', 'hedge_percentage_short', ('auto',)),
        ('Стоп Лосс', 'Тейк Профит Хеджа', 'hedge_stop_loss_percentage', ('auto', 'manually')),
        ('Кредитное плечо', 'Кредитное плечо', 'leverage', ('auto', 'manually')),
    ]

    for text_auto, text_manually, callback_data, modes in all_buttons:
        if trading_mode in modes:
            # Выбираем название в зависимости от режима
            text = text_auto if trading_mode == 'auto' else text_manually
            markup.row(InlineKeyboardButton(text=text, callback_data=callback_data))

    # Общие кнопки
    markup.row(InlineKeyboardButton(text="Назад", callback_data="admin_menu"))

    return markup.as_markup()

def admin_user_cancel_menu(user:User):
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Назад",callback_data="cancel_user:user.id"))
    return markup.as_markup()
def admin_cancel_menu():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Назад",callback_data="admin_menu"))
    return markup.as_markup()
