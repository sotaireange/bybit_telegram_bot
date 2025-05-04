from typing import Sequence
from app.db.models import User

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


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


def are_you_sure():
    markup = InlineKeyboardMarkup()
    markup.row(InlineKeyboardButton(text='Да',callback_data="yes_stop"))
    markup.row(InlineKeyboardButton(text='Нет',callback_data="admin_menu"))
    return markup.as_markup()


def admin_settings_menu():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Объем Лонг",callback_data="volume_long"))
    markup.row(InlineKeyboardButton(text="Объем Шорт",callback_data="volume_short"))
    markup.row(InlineKeyboardButton(text="Процент Лонг",callback_data="long_percentage"))
    markup.row(InlineKeyboardButton(text="Процент Шорт",callback_data="short_percentage"))
    markup.row(InlineKeyboardButton(text="Процент баланса от общего",callback_data="size")) #1-5
    markup.row(InlineKeyboardButton(text="Максимальный баланс",callback_data="balance")) #30-70
    markup.row(InlineKeyboardButton(text="Процент прибыли(Take Profit)",callback_data="take_profit")) #5-30
    markup.row(InlineKeyboardButton(text="Процент Хеджа",callback_data="hedge_percentage")) #5-30
    markup.row(InlineKeyboardButton(text="Кредитное плечо",callback_data="leverage")) # 1-20
    markup.row(InlineKeyboardButton(text="Назад",callback_data="admin_menu"))
    return markup.as_markup()


def admin_user_cancel_menu(user:User):
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Назад",callback_data="cancel_user:user.id"))
    return markup.as_markup()
def admin_cancel_menu():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Назад",callback_data="admin_menu"))
    return markup.as_markup()
