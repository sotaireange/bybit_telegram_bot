from typing import Dict,Sequence
from datetime import datetime

from app.db.models import User


from app.telegram.utils.messages import MessageBuilder


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
        text='Потом придумаю'
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
    def get_user_text(cls,user: User,pnl: Dict[datetime,float],is_run: bool) -> str:
        text=f'{user.username}: id - {user.id} {'ON' if is_run else 'OFF'}\n'
        text+=cls.get_sub_text(user)
        #text+=get_settings_text(user)
        text+=cls.get_stock_text(user)
        if pnl:
            text+= cls.get_pnl_text(pnl)
        return text


    def get_global_settings_text(data:Dict) -> str:
        text=(f'Настройка монет:'
              f'Объем Лонг : {data['volume_long']}$\n'
              f'Объем Шорт : {data['volume_short']}$\n'
              f'Процент лонг : {data['long_percentage']}%\n'
              f'Процент Шорт : {data['short_percentage']}%\n'
              f'Настройка торговли:\n'
              f'Процент баланса от общего: {data['size']}$\n'
              f'Максимальный баланс : {data['balance']}$\n'
              f'Процент прибыли(Take Profit : {data['take_profit']}%\n'
              f'Процента Хеджа : {data['hedge_percentage']}\n'
              f'Кредитное плечо : {data['leverage']}%\n'
              )
        return text



msg=AdminMsgBuilder()
