from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

categories = ["Документы", "Учебный процесс", "Служба заботы", "Другое"]

def get_main_keyboard(disabled_category: str | None = None):
    keyboard = []
    for cat in categories:
        if cat == disabled_category:
            continue
        keyboard.append([InlineKeyboardButton(text=cat, callback_data=cat)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_submenu_keyboard(category: str):
    if category == "Другое":
        buttons = [
            InlineKeyboardButton(text="Проблемы с техникой", callback_data="Проблемы с техникой"),
            InlineKeyboardButton(text="Обратная связь", callback_data="Обратная связь"),

        ]

    buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"))
    return InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])