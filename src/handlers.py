from aiogram import types
from aiogram.types import FSInputFile
from src.keyboard import get_main_keyboard

categories = ["Документы", "Учебный процесс", "Служба заботы", "Другое"]

category_pictures = {
    "Документы": "images/documents.jpg",
    "Учебный процесс": "images/study.jpg",
    "Служба заботы": "images/support.jpg",
    "Другое": "images/other.jpg",
}

category_texts = {
    "Документы": "Тебе поможет учебный отдел, он находится 4 этаже рядом с кабинетом 4.2",
    "Учебный процесс": "Ты можешь обратиться на свою кафедру. Они находятся на 4 этаже напротив столовой",
    "Служба заботы": "Обратись в кабнет службы заботы на 3 этаже рядом с кабинетом 3.8",
    "Другое": "Разные полезные сведения.",
}

user_last_message = {}

async def start_handler(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}!\nЯ знаю, что у тебя вопрос и я постараюсь его решить ❤️",
        reply_markup=get_main_keyboard()
    )

async def callback_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if data in categories:
        if user_id in user_last_message:
            try:
                await callback.message.bot.delete_message(
                    chat_id=callback.message.chat.id,
                    message_id=user_last_message[user_id]
                )
            except Exception:
                pass  

        photo_path = category_pictures.get(data)
        text = category_texts.get(data, "")

        if photo_path:
            photo = FSInputFile(photo_path)
            sent = await callback.message.answer_photo(photo, caption=text)
        else:
            sent = await callback.message.answer(text)

        user_last_message[user_id] = sent.message_id

        await callback.answer()
        await callback.answer("Неизвестная команда", show_alert=True)
