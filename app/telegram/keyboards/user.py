from typing import List,Dict,Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.db.models import Run,Notification,UserAPI
from app.common.config import settings



def main_menu(flag:Run=Run.OFF):
    markup= InlineKeyboardBuilder()
    if flag==Run.OFF:
        markup.row(InlineKeyboardButton(text="Включить торговлю",callback_data="run"))
        markup.row(InlineKeyboardButton(text="Включить хедж",callback_data="hedge"))
    elif flag==Run.HEDGE:
        markup.row(InlineKeyboardButton(text="Включить торговлю",callback_data="run"))
        markup.row(InlineKeyboardButton(text="Выключить",callback_data="unrun"))
    else:
        markup.row(InlineKeyboardButton(text="Отключить полностью торговлю",callback_data="unrun"))
        markup.row(InlineKeyboardButton(text="Не закупать новые монеты",callback_data="hedge"))

    #markup.row(InlineKeyboardButton(text="Настройка",callback_data="settings")) #Была отключена возможность настраивать торговлю
    markup.row(InlineKeyboardButton(text="Настройка биржи",callback_data="stock_menu"))
    markup.row(InlineKeyboardButton(text="Позиции",callback_data="all_positions"))
    markup.row(InlineKeyboardButton(text="Уведомления",callback_data="notification"))
    if settings.TRADING_MODE!='manually':
        markup.row(InlineKeyboardButton(text="Подписка",callback_data="subs_menu"))
    return markup.as_markup()


def position_due_api(names:List[str]):
    markup= InlineKeyboardBuilder()
    for name in names:
        markup.row(InlineKeyboardButton(text=f'Api - {name}',callback_data=f'position_{name}'))
    markup.row(InlineKeyboardButton(text="Назад",callback_data="main_menu"))
    return markup.as_markup()

def settings_menu():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Процент баланса от общего",callback_data="size"))
    markup.row(InlineKeyboardButton(text="Максимальный баланс",callback_data="balance"))
    markup.row(InlineKeyboardButton(text="Процент прибыли(Take Profit)",callback_data="take_profit"))
    markup.row(InlineKeyboardButton(text="Кредитное плечо",callback_data="leverage"))
    markup.row(InlineKeyboardButton(text="Настройка биржи",callback_data="stock_menu"))
    markup.row(InlineKeyboardButton(text="Назад",callback_data="main_menu"))
    return markup.as_markup()



def stock_menu(run:bool=True,name:str=None,id:int=None):
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Проверить API",callback_data=f"check_{name}"))
    markup.row(InlineKeyboardButton(text="Api Key",callback_data=f"api_{name}"))
    if name:
        markup.row(InlineKeyboardButton(text="Api Secret",callback_data=f"secret_{name}"))
    if settings.TRADING_MODE=='manually' or (id in settings.ADMIN_IDS):
        markup.row(InlineKeyboardButton(text="Отключить" if run else 'Включить' ,callback_data=f"switch_{name}"))
        markup.row(InlineKeyboardButton(text="Удалить",callback_data=f"delete_{name}"))
    markup.row(InlineKeyboardButton(text="Назад",callback_data=f"main_menu"))
    return markup.as_markup()


#

def new_stock_menu(apis:Sequence[UserAPI]):
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Новый ключ",callback_data=f"new_api_key"))
    for api in apis:
        markup.row(InlineKeyboardButton(text=api.name,callback_data=f"stockapi_{api.name}"))
    markup.row(InlineKeyboardButton(text="Назад",callback_data=f"main_menu"))
    return markup.as_markup()


def all_positions(apis:Sequence[UserAPI]):
    markup= InlineKeyboardBuilder()
    for api in apis:
        markup.row(InlineKeyboardButton(text=api.name,callback_data=f"position_{api.name}"))
    markup.row(InlineKeyboardButton(text="Назад",callback_data="main_menu"))
    return markup.as_markup()

def position_update(api_name:str):
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Обновить",callback_data=f"position_{api_name}"))
    markup.row(InlineKeyboardButton(text="Назад",callback_data="main_menu"))
    return markup.as_markup()


def cancel_menu():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Отменить",callback_data="main_menu"))
    return markup.as_markup()

def notification_menu(notification:Notification):
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text=f"{'🔴Выкл' if notification.main_open else '🟢Вкл'} вход основной",callback_data="main_open"))
    markup.row(InlineKeyboardButton(text=f"{'🔴Выкл' if notification.main_close else '🟢Вкл'} выход основной",callback_data="main_close"))
    markup.row(InlineKeyboardButton(text=f"{'🔴Выкл' if notification.hedge_open else '🟢Вкл'} вход хедж",callback_data="hedge_open"))
    markup.row(InlineKeyboardButton(text=f"{'🔴Выкл' if notification.hedge_close else '🟢Вкл'} выход хедж",callback_data="hedge_close"))
    markup.row(InlineKeyboardButton(text="Назад",callback_data="main_menu"))
    return markup.as_markup()


def proof_to_exit_orders():
    markup = InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text=f'ДА!',callback_data="yes_exit"))
    return markup.as_markup()