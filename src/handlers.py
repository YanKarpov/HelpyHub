from aiogram import types
from aiogram.types import FSInputFile
from src.keyboard import get_main_keyboard

categories = ["Документы", "Учебный процесс", "Служба заботы", "Другое"]

category_pictures = {
    "Документы": "images/documents.jpg",
    "Учебный процесс": "images/study.jpg",
    "Служба заботы": "images/support.jpg",
}

async def start_handler(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}!\nЯ знаю, что у тебя вопрос и я постараюсь его решить ❤️",
        reply_markup=get_main_keyboard()
    )

async def callback_handler(callback: types.CallbackQuery):
    data = callback.data

    if data in categories:
        photo_path = category_pictures.get(data)
        if photo_path:
            photo = FSInputFile(photo_path)  
            await callback.message.answer_photo(photo)
        await callback.answer()
    else:
        await callback.answer("Неизвестная команда", show_alert=True)