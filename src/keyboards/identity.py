from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.keyboards.main_menu import back_button  

def get_identity_choice_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="Отправить анонимно", callback_data="send_anonymous"),
        InlineKeyboardButton(text="Я не против назвать себя", callback_data="send_named"),
    ]

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons] + [[back_button()]])
    return keyboard
