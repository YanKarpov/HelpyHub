import asyncio
import sys

from src.bot import dp, bot, register_handlers, redis_client
from src.logger import setup_logger

logger = setup_logger(__name__)

async def check_redis():
    try:
        pong = await redis_client.ping()
        if pong:
            logger.info("Redis доступен и отвечает.")
        else:
            logger.error("Redis не отвечает на ping! Ты поднял Docker контейнер?")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Ошибка подключения к Redis: {e}")
        sys.exit(1)

async def main():
    await check_redis()  

    register_handlers(dp)  

    logger.info("Бот запущен и ждёт команды.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        logger.info("Запуск бота...")
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
