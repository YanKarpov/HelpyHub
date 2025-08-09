from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def back_button() -> InlineKeyboardButton:
    """Универсальная кнопка 'Назад' для добавления в клавиатуры"""
    return InlineKeyboardButton(text="⬅️ Назад", callback_data="back")

def get_main_keyboard(disabled_category: str = None) -> InlineKeyboardMarkup:
    """Основное меню с категориями, одна из которых может быть неактивной"""
    buttons = []
    categories = ["Документы", "Учебный процесс", "Служба заботы", "Другое"]

    for cat in categories:
        if cat == disabled_category:
            buttons.append([InlineKeyboardButton(text=f"• {cat}", callback_data="ignore")])
        else:
            buttons.append([InlineKeyboardButton(text=cat, callback_data=cat)])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_submenu_keyboard(category: str) -> InlineKeyboardMarkup:
    """Подменю для выбранной категории с добавлением кнопки 'Назад'"""
    buttons = []

    if category == "Другое":
        buttons.extend([
            InlineKeyboardButton(text="Проблемы с техникой", callback_data="Проблемы с техникой"),
            InlineKeyboardButton(text="Обратная связь", callback_data="Обратная связь"),
            InlineKeyboardButton(text="Срочная помощь", callback_data="Срочная помощь"),
        ])

    buttons.append(back_button())
    # Каждая кнопка в отдельном ряду
    return InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
