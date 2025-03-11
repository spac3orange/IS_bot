from aiogram.utils.keyboard import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

def search_by():
    kb_builder = InlineKeyboardBuilder()
    kb_builder.button(text="Модель", callback_data=f"search_model")
    kb_builder.button(text="Штрихкод", callback_data=f"search_code")
    kb_builder.adjust(2)
    return kb_builder.as_markup(resize_keyboard=True)