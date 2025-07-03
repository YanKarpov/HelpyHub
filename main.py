import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

def get_category_keyboard():
    keyboard = [
        [InlineKeyboardButton(text="Документы", callback_data="cat_documents")],
        [InlineKeyboardButton(text="Учебный процесс", callback_data="cat_study")],
        [InlineKeyboardButton(text="Служба заботы", callback_data="cat_support")],
        [InlineKeyboardButton(text="Другое", callback_data="cat_other")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}!\nЯ знаю, что у тебя вопрос и я постараюсь его решить  ❤️",
        reply_markup=get_category_keyboard()
    )

@dp.callback_query()
async def category_callback_handler(callback: CallbackQuery):
    data = callback.data
    categories = {
        "cat_documents": "Вы выбрали *Документы*.",
        "cat_study": " Вы выбрали *Учебный процесс*.",
        "cat_support": " Вы выбрали *Службу заботы*.",
        "cat_other": "Вы выбрали *Другое*.",
    }

    response = categories.get(data, "Неизвестная категория.")
    await callback.message.answer(response, parse_mode="Markdown")
    await callback.answer()  

async def main():
    logger.info("Бот запущен и ждёт команды.")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        logger.info("Запуск бота...")
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
