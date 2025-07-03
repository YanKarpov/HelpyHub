from aiogram import types
from aiogram.types import CallbackQuery

from src.keyboard import get_main_keyboard, get_submenu_keyboard

responses = {
    "doc_certificates": "Информация будет",
    "doc_statements": "Информация будет",
    "doc_orders": "Информация будет",
    "doc_accepts": "Информация будет",
    "doc_money": "Информация будет",
    "study_schedule": "Расписание занятий доступно на сайте.",
    "study_exams": "Ближайшие экзамены пройдут через месяц.",
    "support_tech": "Техподдержка работает с 9:00 до 18:00.",
    "support_psych": "Психолог доступен по записи.",
    "other_feedback": "Спасибо за обратную связь!",
    "other_questions": "Задайте ваши вопросы здесь.",
}

async def start_handler(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}!\nЯ знаю, что у тебя вопрос и я постараюсь его решить ❤️",
        reply_markup=get_main_keyboard()
    )

async def callback_handler(callback: CallbackQuery):
    data = callback.data

    if data == "back_to_main":
        await callback.message.edit_text(
            f"Привет, {callback.from_user.full_name}!\nВыбери категорию:",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return

    if data in ["cat_documents", "cat_study", "cat_support", "cat_other"]:
        await callback.message.edit_text(
            "Вы выбрали категорию. Пожалуйста, выберите один из вариантов ниже:",
            reply_markup=get_submenu_keyboard(data)
        )
        await callback.answer()
        return

    if data in responses:
        await callback.message.answer(responses[data])
        await callback.answer()
        return

    await callback.answer("Неизвестная команда.", show_alert=True)
