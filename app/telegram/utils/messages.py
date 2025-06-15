import pandas as pd
from typing import Dict,List
import logging

from app.db.models import User,TelegramMessage,NotificationType,PositionType,Run,Payment,Notification
from app.telegram.utils.sub_helper import get_sub_days
from datetime import datetime,timedelta
import pytz

logger=logging.getLogger('aiogram')


class MessageBuilder:
    translations = {
        "leverage": "Кредитное плечо",
        "balance": "Баланс",
        "take_profit": "Тейк-профит",
        "size": "Размер сделки",
        "api": "API ключ",
        "secret": "API Secret",
        "user_sub": "Количество дней подписки",
        'hedge_percentage': "Процент открытия хэджирования",
        'hedge_stop_loss_percentage' : "Стоп лос Хеджирования"
    }
    url_info= {
        'api_secret_url':'https://telegra.ph/Instrukciya-po-sozdaniyu-i-nastrojke-API-klyuchej-na-kriptobirzhe-Bybit-06-08-2'
    }

    templates = {
        "welcome": "Дорогие друзья, всех приветствуем. "
                   "Вы находитесь на нашем полностью автоматизированном торговом боте который торгует криптовалютой (трейдинг), он разрабатывался по нашей авторской стратегии командой профессиональных трейдеров на протяжении 3-х лет."
                   "Мы не берем никаких платежей заранее, не оформляем никакие платные подписки, Вы оплачиваете только процент с прибыли заработанной ботом, торговля на боте осуществляется от 10$, средний процент прибыли в месяц от 70% от Вашего депозита,"
                   "подключение через API-ключи. Для Вас работа с нашим ботом максимально безопасна, деньги мы ваши вывести или куда то перевести не можем, бот работает только на торговлю с криптовалютой (в настройках API-ключей Вы сами все настраиваете). "
                   "Наша служба технической поддержки ответит на любые Ваши вопросы и поможет провести все необходимые настройки\n"
                   "Администратор: @Gellert_I",
        "api_secret_info": f'Введите API Key и API Secret полученные на бирже.\n'
                           f''
                           f'<a href="{url_info['api_secret_url']}">Инструкция</a>',
        "api_info": "Введите API",
        "secret_info": "Введите SECRET",
        "api_secret_success": "Вы успешно подключились в боту",
        "api_secret_fail": "Упс, что то пошло не так",
        "settings_title": "Настройки:",
        "input_setting": "Укажите {0}.\nВведите значение от {1} до {2}",
        "input_failure": (
            "Неверное значение\n"
            "Вы ввели {0}\n"
            "Допустимые значения от {1} до {2}"
        ),
        "input_success": "Вы изменили {0}.\nНовое значение {1}",
        "value_error": "Ошибка: введите числовое значение.\n",
        "user_when_start": "Вы запустили бота",
        "user_when_stop":"Ваш бот был остановлен.\n",
        "user_when_exit":"Ваш бот был остановлен и вышли из всех позиций.\n",
        "user_subscription":"Выдача подписки на {0} дней.\n",
        "user_unsub":"Ваша подписка аннулирована.\n",
        "user_failed_get_url_pk":"Не удалось получить ссылку на оплату на PayKassa.\n"
                              "Свяжитесь с администратором.",
        "payment_not_need" : "Оплата не требуется",
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
    def get_menu_text(cls, user: User, run:Run):
        if run==Run.ACTIVE:
            text='Включена торговля и Хеджирование'
        elif run==Run.HEDGE:
            text='Включено только хеджирование'
        else:
            text='Бот остановлен'
        text+='\n'
        text+=cls.get_sub_text(user)
        # text+=cls.get_pnl_text(pnl)
        return text

    @classmethod
    def get_position_text(cls,positions: List[Dict]):
        if len(positions)==0:
            return "Позиций нет"
        df=pd.DataFrame(positions)
        df['updatedTime']=df['updatedTime'].astype(int)
        df.sort_values(by=['symbol','updatedTime'],inplace=True,ascending=[False,True])

        last_symbol=''
        text = f"Открытых позиций: {len(positions)}\n"
        text += "<pre>\n"
        text += (f"{'COIN':<9} {'Размер':>8}" #{'Цена':>9}"
                 f" {'Закрытие':>10} {'PNL':>8}\n")

        for idx,position in df.iterrows():
            if not position.any(): continue
            symbol = position['symbol'][:-4]
            side = position['side']
            position_value = cls.safe_round(position['positionValue'])
            leverage= cls.safe_round(position['leverage'])
            position_size=round(position_value/leverage,2)
            #mark_price = cls.safe_round(position.get('markPrice'))
            take_profit_value = position['takeProfit'] or position['stopLoss']
            take_profit_str = cls.format_tp(take_profit_value)
            unrealised_pnl = cls.safe_round(position['unrealisedPnl'])
            side_icon = '🟢' if side == 'Buy' else '🔴'

            if symbol != last_symbol:
                pos_type = "(M)"
            else:
                pos_type = "(H)"


            coin_label = f"{side_icon}{pos_type}{symbol}"

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
    def get_pnl_text(cls,pnls:pd.DataFrame) -> str:
        text='Профит:\n'
        if len(pnls):
            text=f'Общий за 3 месяца: {pnls['closedPnl'].sum()}$\n'
            month_now=datetime.now().month
            for month in range(month_now,month_now-3,-1):
                pnl=pnls[pnls['updatedTime'].dt.month==month]['closedPnl'].sum()
                text+=f'{cls.months[month]}: {round(pnl,2)}$\n'
        else:
            text='Общий профит:0\n'

        return text

    @classmethod
    def get_sub_text(cls, user: User) -> str:
        delta = get_sub_days(user)
        days = delta.days
        hours, remainder = divmod(delta.seconds, 3600)
        minutes = remainder // 60

        # Форматируем вывод
        formatted = f"{days}д. {hours:02}ч. {minutes:02} мин."
        return f'Подписка  {formatted}\n' if days>0 else "Нужно оплатить подписку\n"

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
        text=f'API - {api_text}\nSecret Key - {secret_text}\n'
        if not user.api or not user.secret:
            text+= cls.templates['api_secret_info']
        return text

    @classmethod
    def send_order_notification(cls, msg: TelegramMessage) -> str:
        data=msg.data
        if msg.type==NotificationType.POSITION_OPEN:
            text_open='Открытие'
        else:
            text_open='Закрытие'
        text_side= "'🟢'" if data.position_idx==1 else '🔴'
        text_position_type='MAIN' if data.position_type==PositionType.MAIN else "HEDGE"
        text_amount=round(cls.safe_round(data.amount)*cls.safe_round(data.leverage),2)
        text_position=(f'{text_side}{text_open} {text_position_type}\n'
                       f'{data.symbol} {text_amount}$\n'
                       f'')
        return text_position

    @classmethod
    def get_subs_text(self,user:User,payment:Payment):
        if payment.amount>0:
            text=(f'Сумма оплаты: {payment.amount}$')
        else:
            text='Оплата не требуется'
        return text



    @classmethod
    def get_succes_payment_text(self,payment:Payment):
        text=(f'Сумма оплаты: {payment.amount}$\n'
              f'Оплата завершена: {(payment.completed_at + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M:%S")}')
        return text

    def get_notification_text(self,notification:Notification):
        text=(f'Уведомления:\n'
              f'Открытие основной {"🟢" if notification.main_open else "🔴"}\n'
              f'Закрытие основной {"🟢" if notification.main_close else "🔴"}\n'
              f'Открытие Хеджирование {"🟢" if notification.hedge_open else "🔴"}\n'
              f'Закрытие Хэджирование {"🟢" if notification.hedge_close else "🔴"}\n')
        return text


msg=MessageBuilder()