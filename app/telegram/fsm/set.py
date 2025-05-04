from aiogram.fsm.state import State, StatesGroup


class Set(StatesGroup):
    LEVERAGE=State()
    TAKE_PROFIT=State()
    SIZE=State()
    BALANCE=State()
    API=State()
    SECRET=State()
