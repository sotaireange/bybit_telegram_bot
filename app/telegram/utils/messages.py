import pandas as pd
from typing import Dict,List

from app.db.models import User
from app.telegram.utils.sub_helper import get_sub_days
from datetime import datetime

class MessageBuilder:
    translations = {
        "leverage": "Кредитное плечо",
        "balance": "Баланс",
        "take_profit": "Тейк-профит",
        "size": "Размер сделки",
        "api": "API ключ",
        "secret": "API Secret",
        "user_sub": "Количество дней подписки",
        'hedge_percentage': "Процент Хеджа"
    }

    templates = {
        "welcome": "Приветственное сообщение о боте!!!",
        "api_secret_info": "Введите API/Secret, а потом проверьте доступы по кнопке ниже",
        "api_info": "Инструкция по вводу API",
        "secret_info": "Инструкция по вводу SECRET",
        "api_secret_success": "Успешное подключение к API",
        "api_secret_fail": "Неуспешное подключение к API",
        "settings_title": "Настройки:",
        "input_setting": "Укажите {0}.\nВведите значение от {1} до {2}",
        "input_failure": (
            "Неверное значение\n"
            "Вы ввели {0}\n"
            "Допустимые значения от {1} до {2}"
        ),
        "input_success": "Вы изменили {0}.\nНовое значение {1}",
        "value_error": "Ошибка: введите числовое значение.\n",
        "user_when_stop":"Ваш бот был остановлен.\n",
        "user_when_exit":"Ваш бот был остановлен и вышли из всех позиций.\n",
        "user_subscription":"Выдача подписки на {0} дней.\n",
        "user_unsub":"Ваша подписка аннулирована.\n",

    }

    months = {
        1: 'Январь',
        2: 'Февраль',
        3: 'Март',
        4: 'Апрель',
        5: 'Май',
        6: 'Июнь',
        7: 'Июль',
        8: 'Август',
        9: 'Сентябрь',
        10: 'Октябрь',
        11: 'Ноябрь',
        12: 'Декабрь'
    }


    def __init__(self):
        self.translations = self.__class__.translations.copy()
        self.templates = self.__class__.templates.copy()

    def __call__(self, key: str, *args):
        translated_args = [self.translations.get(arg, arg) if isinstance(arg, str) else arg for arg in args]
        template = self.templates.get(key)
        if template:
            return template.format(*translated_args)
        return f"❌ Шаблон '{key}' не найден."

    @staticmethod
    def safe_round(value):
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def format_tp(value):
        try:
            f = float(value)
            if f == 0:
                return "0".rjust(8)
            return f"{f:.6f}"[:8].rjust(8)
        except (TypeError, ValueError):
            return "0".rjust(8)

    @classmethod
    def get_menu_text(cls,user:User,pnl: Dict[datetime,float],flag_run:bool):
        text='Бот работает\n' if flag_run else 'Бот не работает\n'
        text+=cls.get_sub_text(user)
        text+=cls.get_pnl_text(pnl)
        return text

    @classmethod
    def get_position_text(cls,positions: List[Dict]):

        if len(positions)==0: return 'Позиций нет'
        df=pd.DataFrame(positions)
        df['updatedTime']=df['updatedTime'].astype(int)
        df.sort_values(by=['symbol','updatedTime'],inplace=True,ascending=[False,True])

        last_symbol=''
        text = f"Открытых позиций: {len(positions)}\n"
        text += "<pre>\n"
        text += (f"{'COIN':<9} {'Размер':>8}" #{'Цена':>9}"
                 f" {'Тейк':>10} {'PNL':>8}\n")

        for position in positions:
            symbol = position.get('symbol', '—')[:-4]
            side = position.get('side', '')
            position_value = cls.safe_round(position.get('positionValue'))
            leverage= cls.safe_round(position.get('leverage'))
            position_size=round(position_value/leverage,2)
            #mark_price = cls.safe_round(position.get('markPrice'))
            take_profit_value = position.get('takeProfit') or 0
            take_profit_str = cls.format_tp(take_profit_value)
            unrealised_pnl = cls.safe_round(position.get('unrealisedPnl'))
            side_icon = '🟢' if side == 'Buy' else '🔴'

            coin_label = f"{side_icon}{symbol}"
            if symbol != last_symbol:
                coin_label += "(F)"
            else:
                coin_label += "(S)"

            text += (f"{coin_label:<9} {position_size:>6.2f}$" #{mark_price:>9.2f}$ "
                     f"{take_profit_str:>10}$ {unrealised_pnl:>8.2f}$\n")
            last_symbol = symbol

        text += "</pre>"
        return text


    @classmethod
    def get_permission_text(cls, has_permission: Dict) -> str:
        if not has_permission['has_api_secret']: return 'Не указан API/Secret\n'
        extra = (f'{'Чтение и запись.\n' if not has_permission['readonly'] else ''}'
                 f'{'Единый торговый аккаунт: Ордера, Позиции, Торговля дериативами USDC.' if not has_permission['permissions'] else ''}')
        return f"Все доступы имеются\n Ваш BybitUID {has_permission['result'].get('parentUid')}" if has_permission['status'] else f"Подключите доступы: \n{extra}"

    @classmethod
    def get_pnl_text(cls,pnls:Dict[datetime,float]) -> str:
        text='Профит:\n'
        for month,pnl in pnls.items():
            text+=f'{cls.months[month.month]}: {round(pnl,2)}$\n'
        if not len(pnls): return 'Профит: нет данных'
        return text

    @classmethod
    def get_sub_text(cls, user: User) -> str:
        days = get_sub_days(user)
        return f'Подписка осталось {abs(days)} дней.\n' if days < 0 else "Подписка неактивна\n"

    @classmethod
    def get_settings_text(cls, user: User) -> str:
        return (
            f'{cls.templates["settings_title"]} \n'
            f'Стоимость ордера - {user.size}%\n'
            f'Баланс - {user.balance}%\n'
            f'Кредитное плечо - {user.leverage}\n'
            f'Тейк профит - {user.take_profit}%\n'
        )

    @classmethod
    def get_stock_text(cls, user: User) -> str:
        api_text = user.api if user.api else 'Не указан'
        secret_text = user.secret if user.secret else 'Не указан'
        return f'API - {api_text}\nSecret Key - {secret_text}\n'


msg=MessageBuilder()