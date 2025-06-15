from aiogram.fsm.state import State, StatesGroup


class AdminSet(StatesGroup):
    VOLUME_LONG=State()
    VOLUME_SHORT=State()
    LONG_PERCENTAGE=State()
    SHORT_PERCENTAGE=State()
    LEVERAGE=State()
    SIZE=State()
    BALANCE=State()
    TAKE_PROFIT=State()
    HEDGE_PERCENTAGE=State()
    HEDGE_STOP_LOSS_PERCENTAGE=State()

    NOT_SET=State()

class AdminUserSet(StatesGroup):
    SUB=State()