from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.db.models import Run

def main_menu(flag:Run=Run.OFF):
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Обновить",callback_data="main_menu"))
    if flag==Run.OFF:
        markup.row(InlineKeyboardButton(text="Включить торговлю",callback_data="run"))
    else:
        markup.row(InlineKeyboardButton(text="Отключить торговлю",callback_data="unrun"))
    #markup.row(InlineKeyboardButton(text="Настройка",callback_data="settings")) #Была отключена возможность настраивать торговлю
    markup.row(InlineKeyboardButton(text="Настройка биржи",callback_data="stock_menu"))
    markup.row(InlineKeyboardButton(text="Позиции",callback_data="positions"))
    markup.row(InlineKeyboardButton(text="Подписка",callback_data="subs"))
    return markup.as_markup()

def settings_menu():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Процент баланса от общего",callback_data="size")) #1-5
    markup.row(InlineKeyboardButton(text="Максимальный баланс",callback_data="balance")) #30-70
    markup.row(InlineKeyboardButton(text="Процент прибыли(Take Profit)",callback_data="take_profit")) #5-30
    markup.row(InlineKeyboardButton(text="Кредитное плечо",callback_data="leverage")) # 1-20
    markup.row(InlineKeyboardButton(text="Настройка биржи",callback_data="stock_menu"))
    markup.row(InlineKeyboardButton(text="Назад",callback_data="main_menu"))
    return markup.as_markup()


def stock_menu():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Проверить API",callback_data="check_api")) # 1-20
    markup.row(InlineKeyboardButton(text="Api Key",callback_data="api")) #30-70
    markup.row(InlineKeyboardButton(text="Api Secret",callback_data="secret")) #5-10
    markup.row(InlineKeyboardButton(text="Назад",callback_data="main_menu")) #5-10
    return markup.as_markup()


def cancel_menu():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Отменить",callback_data="main_menu"))
    return markup.as_markup()