from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard(disabled_category: str = None):
    buttons = []
    for cat in ["Документы", "Учебный процесс", "Служба заботы", "Другое"]:
        if cat == disabled_category:
            buttons.append([InlineKeyboardButton(text=f"• {cat}", callback_data="ignore")])
        else:
            buttons.append([InlineKeyboardButton(text=cat, callback_data=cat)])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_submenu_keyboard(category: str):
    buttons = []

    if category == "Другое":
        buttons.extend([
            InlineKeyboardButton(text="Проблемы с техникой", callback_data="Проблемы с техникой"),
            InlineKeyboardButton(text="Обратная связь", callback_data="Обратная связь"),
            InlineKeyboardButton(text="Срочная помощь", callback_data="urgent_help"), 
        ])

    buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"))
    return InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])

def get_identity_choice_keyboard():
    buttons = [
        InlineKeyboardButton(text="Отправить анонимно", callback_data="send_anonymous"),
        InlineKeyboardButton(text=" Я не против назвать себя", callback_data="send_named"),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])


def get_reply_to_user_keyboard(user_id: int):
    """Клавиатура с кнопкой 'Ответить' для админов."""
    button = InlineKeyboardButton(
        text="Ответить", callback_data=f"reply_to_user:{user_id}"
    )
    return InlineKeyboardMarkup(inline_keyboard=[[button]])