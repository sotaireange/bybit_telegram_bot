from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder



def subs_menu():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Сколько нужно заплатить?",callback_data="sub_amount"))
    markup.row(InlineKeyboardButton(text="FreeKassa",callback_data="freekassa"))
    markup.row(InlineKeyboardButton(text="PayKassa",callback_data="paykassa"))
    markup.row(InlineKeyboardButton(text="Crypto Wallet",callback_data="crypto_wallet"))
    markup.row(InlineKeyboardButton(text="Главное меню",callback_data="main_menu"))
    return markup.as_markup()


def free_kassa_gen():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Сгенерировать ссылку",callback_data="freekassa_gen"))
    markup.row(InlineKeyboardButton(text="Назад",callback_data="subs_menu"))
    return markup.as_markup()

def cancel_subs():
    markup= InlineKeyboardBuilder()
    markup.row(InlineKeyboardButton(text="Отменить",callback_data="subs_cancel"))
    return markup.as_markup()
