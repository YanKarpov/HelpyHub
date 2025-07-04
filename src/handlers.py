from aiogram import types
from aiogram.types import FSInputFile
from src.keyboard import get_main_keyboard, get_submenu_keyboard
from aiogram.types import InputMediaPhoto

categories = ["Документы", "Учебный процесс", "Служба заботы", "Другое"]

category_pictures = {
    "Документы": "images/documents.jpg",
    "Учебный процесс": "images/study.jpg",
    "Служба заботы": "images/support.jpg",
    "Другое": "images/other.webp", 

}

category_texts = {
    "Документы": "Тебе поможет учебный отдел, он находится на 4 этаже рядом с кабинетом 4.2",
    "Учебный процесс": "Ты можешь обратиться на свою кафедру. Она находится на 4 этаже напротив столовой",
    "Служба заботы": "Обратись в кабинет службы заботы на 3 этаже рядом с кабинетом 3.8",
    "Другое": "Разные полезные сведения.",
}

user_last_message = {}

async def start_handler(message: types.Message):
    welcome_text = (
        f"Привет, {message.from_user.full_name}!\n"
        "Я знаю, что у тебя вопрос и я постараюсь его решить ❤️"
    )
    photo_path = "images/other.webp" 

    await message.answer_photo(
        photo=FSInputFile(photo_path),
        caption=welcome_text,
        reply_markup=get_main_keyboard()
    )


async def callback_handler(callback: types.CallbackQuery):
    data = callback.data

    if data == "back_to_main":
        welcome_text = (
            f"Привет, {callback.from_user.full_name}!\n"
            "Я знаю, что у тебя вопрос и я постараюсь его решить ❤️"
        )
        photo_path = "images/other.webp" 

        media = InputMediaPhoto(media=FSInputFile(photo_path), caption=welcome_text)

        try:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.edit_media(media=media, reply_markup=get_main_keyboard())
        except Exception as e:
            await callback.message.answer_photo(
                photo=FSInputFile(photo_path),
                caption=welcome_text,
                reply_markup=get_main_keyboard()
            )

        await callback.answer()
        return



    if data == "ignore":
        await callback.answer("Вы уже здесь 😉", show_alert=True)
        return

    if data == "Другое":
        text = category_texts.get("Другое", "Информация не найдена.")
        photo_path = category_pictures.get("Другое")
        submenu = get_submenu_keyboard("Другое")

        if photo_path:
            media = InputMediaPhoto(media=FSInputFile(photo_path), caption=text)
            try:
                # Удаляем старые кнопки, меняем фото и кнопки на подменю
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.edit_media(media=media, reply_markup=submenu)
            except Exception:
                # Если не удалось отредактировать — отправляем новое сообщение (крайний случай)
                await callback.message.answer_photo(
                    photo=FSInputFile(photo_path),
                    caption=text,
                    reply_markup=submenu
                )
        else:
            # Если фото нет — редактируем просто текст и кнопки
            try:
                await callback.message.edit_text(text=text, reply_markup=submenu)
            except Exception:
                await callback.message.answer(text=text, reply_markup=submenu)

        await callback.answer()
        return


    if data in categories:
        # Для остальных категорий с фото
        text = category_texts.get(data, "Информация не найдена.")
        photo_path = category_pictures.get(data)
        keyboard = get_main_keyboard(disabled_category=data)

        if photo_path:
            media = InputMediaPhoto(media=FSInputFile(photo_path), caption=text)
            try:
                # Убираем старые кнопки, меняем фото и ставим новые кнопки
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.edit_media(media=media, reply_markup=keyboard)
            except Exception:
                # Если не удалось — отправляем новое сообщение с фото и кнопками (редко, но на всякий случай)
                await callback.message.answer_photo(
                    photo=FSInputFile(photo_path),
                    caption=text,
                    reply_markup=keyboard
                )
        else:
            try:
                await callback.message.edit_text(text=text, reply_markup=keyboard)
            except Exception:
                await callback.message.answer(text=text, reply_markup=keyboard)

        await callback.answer()
        return

    await callback.answer("Неизвестная команда", show_alert=True)
