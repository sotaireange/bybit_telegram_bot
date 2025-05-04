from aiogram.fsm.state import State, StatesGroup


class AdminSet(StatesGroup):
    VOLUME_LONG=State()
    VOLUME_SHORT=State()
    LONG_PERCENTAGE=State()
    SHORT_PERCENTAGE=State()

    NOT_SET=State()

class AdminUserSet(StatesGroup):
    SUB=State()