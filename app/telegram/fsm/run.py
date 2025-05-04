from aiogram.fsm.state import State, StatesGroup


class Main(StatesGroup):
    RUN = State()
    UNRUN = State()
