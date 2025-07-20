def get_identity_choice_keyboard():
    buttons = [
        InlineKeyboardButton(text="Отправить анонимно", callback_data="send_anonymous"),
        InlineKeyboardButton(text=" Я не против назвать себя", callback_data="send_named"),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
