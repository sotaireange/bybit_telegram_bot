from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder



def subs_menu(amount:float):
    markup= InlineKeyboardBuilder()
    # markup.row(InlineKeyboardButton(text="Сколько нужно заплатить?",callback_data="subs_menu"))
    if float:
        #markup.row(InlineKeyboardButton(text="FreeKassa",callback_data="free_kassa"))
        markup.row(InlineKeyboardButton(text="PayKassa",callback_data="pay_kassa"))
        #markup.row(InlineKeyboardButton(text="Crypto Wallet",callback_data="crypto_wallet"))
    markup.row(InlineKeyboardButton(text="Главное меню",callback_data="main_menu"))
    return markup.as_markup()






def payment_url(url:str):
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Оплатить",url=url))
    markup.row(InlineKeyboardButton(text="Назад",callback_data="subs_menu"))
    return markup.as_markup()

def cancel_subs():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Отменить",callback_data="subs_cancel"))
    return markup.as_markup()
