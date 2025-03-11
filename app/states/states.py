from aiogram.fsm.state import StatesGroup, State


class SearchQuery(StatesGroup):
    input_model = State()
    input_code = State()