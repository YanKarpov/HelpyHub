from aiogram import types
from aiogram.filters import Command
from src.utils.config import GROUP_CHAT_ID
from src.services.redis_client import redis_client
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

async def block_user_handler(message: types.Message):
    if message.chat.id != GROUP_CHAT_ID:
        await message.answer("❌ Команда доступна только в группе поддержки.")
        return

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer("Использование: /block_user <user_id> [время_блокировки_в_минутах]")
        return

    user_id = int(args[1])
    block_minutes = 60
    if len(args) == 3 and args[2].isdigit():
        block_minutes = int(args[2])

    await redis_client.set(f"blocked:{user_id}", "1", ex=block_minutes * 60)
    logger.info(f"User {user_id} заблокирован на {block_minutes} минут (команда в группе {GROUP_CHAT_ID})")
    await message.answer(f"Пользователь {user_id} заблокирован на {block_minutes} минут.")

async def unblock_user_handler(message: types.Message):
    if message.chat.id != GROUP_CHAT_ID:
        await message.answer("❌ Команда доступна только в группе поддержки.")
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer("Использование: /unblock_user <user_id>")
        return

    user_id = int(args[1])
    await redis_client.delete(f"blocked:{user_id}")
    logger.info(f"User {user_id} разблокирован (команда в группе {GROUP_CHAT_ID})")
    await message.answer(f"Пользователь {user_id} разблокирован.")
