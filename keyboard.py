from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="Документы", callback_data="cat_documents")],
        [InlineKeyboardButton(text="Учебный процесс", callback_data="cat_study")],
        [InlineKeyboardButton(text="Служба заботы", callback_data="cat_support")],
        [InlineKeyboardButton(text="Другое", callback_data="cat_other")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_submenu_keyboard(category: str):
    if category == "cat_documents":
        buttons = [
            InlineKeyboardButton(text="Справки", callback_data="doc_certificates"),
            InlineKeyboardButton(text="Заявления", callback_data="doc_statements"),
            InlineKeyboardButton(text="Приказы", callback_data="doc_orders"),
            InlineKeyboardButton(text="Доп.Соглашения", callback_data="doc_accepts"),
            InlineKeyboardButton(text="Счёта на оплату", callback_data="doc_money"),

        ]
    elif category == "cat_study":
        buttons = [
            InlineKeyboardButton(text="Расписание", callback_data="study_schedule"),
            InlineKeyboardButton(text="Экзамены", callback_data="study_exams"),
        ]
    elif category == "cat_support":
        buttons = [
            InlineKeyboardButton(text="Техподдержка", callback_data="support_tech"),
            InlineKeyboardButton(text="Психолог", callback_data="support_psych"),
        ]
    elif category == "cat_other":
        buttons = [
            InlineKeyboardButton(text="Обратная связь", callback_data="other_feedback"),
            InlineKeyboardButton(text="Техника", callback_data="other_questions"),
        ]
    else:
        buttons = []

    buttons.append(InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main"))
    return InlineKeyboardMarkup(inline_keyboard=[[btn] for btn in buttons])
