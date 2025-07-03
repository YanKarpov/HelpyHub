from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="Документы", callback_data="Документы")],
        [InlineKeyboardButton(text="Учебный процесс", callback_data="Учебный процесс")],
        [InlineKeyboardButton(text="Служба заботы", callback_data="Служба заботы")],
        [InlineKeyboardButton(text="Другое", callback_data="Другое")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
