from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_reply_to_user_keyboard(user_id: int):
    button = InlineKeyboardButton(
        text="Ответить", callback_data=f"reply_to_user:{user_id}"
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])
