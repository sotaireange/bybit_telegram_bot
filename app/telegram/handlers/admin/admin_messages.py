from typing import Dict,Sequence
from datetime import datetime
import pandas as pd
from app.db.models import User


from app.telegram.utils.messages import MessageBuilder
from app.common.config import settings

class AdminMsgBuilder(MessageBuilder):
    translations = {
        **MessageBuilder.translations,
        "volume_long": "Объём LONG",
        "volume_short": "Объём SHORT",
        "long_percentage": "Процент LONG",
        "short_percentage": "Процент SHORT"
    }

    templates = {
        **MessageBuilder.templates,
        "input_setting": "Укажите {0}.",
        "input_success": "Вы изменили {0}.\nНовое значение {1}",
        "unsub_success":"Вы отменили подписку id: {0}\n",
        "text_admin_when_stop": "Вы остановили бота id: {0}\n",
        "text_admin_when_exit": 'Вы остановили бота и вышли из всей позиции юзера id: {0}'
    }


    @classmethod
    def get_admin_menu_text(cls) -> str:
        text='Админ меню'
        return text

    @classmethod
    def get_user_admin_text(cls,users: Sequence[User],list_running: Dict) -> str:
        text='Список пользователей:\n'
        for user in users:
            is_run=list_running[user.id]
            is_run_text='ON' if is_run else "OFF"
            text+= f'{user.username}: id-{user.id} {is_run_text}\n'
        return text

    @classmethod
    def get_user_text(cls,user: User,pnl: pd.DataFrame,is_run: bool) -> str:
        text=f'{user.username}: id - {user.id} {'ON' if is_run else 'OFF'}\n'
        text+=cls.get_sub_text(user)
        #text+=get_settings_text(user)
        text+=cls.get_stock_text(user)
        if len(pnl):
            text+= cls.get_pnl_text(pnl)
        return text


    @classmethod
    def get_global_settings_text(cls,data_coin:Dict, data_trade:Dict) -> str:
        trading_mode=settings.TRADING_MODE
        SETTINGS_CONFIG = [
            # Категория 'coin'
            ('coin', 'volume_long', 'Объем Лонг', 'Объем Лонг', '$', ('auto', 'manually')),
            ('coin', 'volume_short', 'Объем Шорт', 'Объем Шорт', '$', ('auto',)),
            ('coin', 'long_percentage', 'Процент Лонг', 'Процент Лонга', '%', ('auto', 'manually')),
            ('coin', 'short_percentage', 'Процент Шорт', 'Процент Шорта', '%', ('auto',)),
            # Категория 'trade'
            ('trade', 'size', 'Процент баланса от общего', 'Процент баланса от общего', '%', ('auto', 'manually')),
            ('trade', 'balance', 'Максимальный баланс', 'Максимальный баланс', '$', ('auto', 'manually')),
            ('trade', 'take_profit', 'Процент прибыли(Take Profit)', 'Тейк Профит Безубытка', '%', ('auto', 'manually')),
            ('trade', 'hedge_percentage_long', 'Процент Хеджа Long', 'Процент Хеджа Long', '%', ('auto',)),
            ('trade', 'hedge_percentage_short', 'Процент Хеджа Short', 'Процент Хеджа Short', '%', ('auto',)),
            ('trade', 'hedge_stop_loss_percentage', 'Стоп Лосс', 'Тейк Профит Хеджа', '%', ('auto', 'manually')),
            ('trade', 'leverage', 'Кредитное плечо', 'Кредитное плечо', '%', ('auto', 'manually')),
        ]
        text_lines = []

        # Добавляем заголовок для настроек монет
        text_lines.append('Настройка монет:')
        for category, key, text_auto, text_manually, suffix, modes in SETTINGS_CONFIG:
            if category == 'coin' and trading_mode in modes:
                label = text_auto if trading_mode == 'auto' else text_manually
                value = data_coin.get(key, 'N/A') # .get() для безопасности
                text_lines.append(f'{label} : {value}{suffix}')

        # Добавляем заголовок для настроек торговли
        text_lines.append('\nНастройка торговли:')
        for category, key, text_auto, text_manually, suffix, modes in SETTINGS_CONFIG:
            if category == 'trade' and trading_mode in modes:
                label = text_auto if trading_mode == 'auto' else text_manually
                value = data_trade.get(key, 'N/A') # .get() для безопасности
                text_lines.append(f'{label} : {value}{suffix}')

        return '\n'.join(text_lines)




msg=AdminMsgBuilder()
