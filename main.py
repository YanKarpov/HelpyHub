import asyncio
import logging

from src.bot import dp, bot, register_handlers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    register_handlers(dp)  

    logger.info("Бот запущен и ждёт команды.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        logger.info("Запуск бота...")
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
