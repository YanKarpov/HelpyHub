from aiogram import types
from config.config import Config
from src.services.redis_client import redis_client
from src.utils.logger import setup_logger
from src.templates.admin_messages import (
    BLOCKED_GROUP_ONLY,
    USAGE_BLOCK_USER,
    USAGE_UNBLOCK_USER,
    BLOCK_USER_SUCCESS,
    UNBLOCK_USER_SUCCESS,
)

logger = setup_logger(__name__)

async def block_user_handler(message: types.Message):
    if message.chat.id != Config.GROUP_CHAT_ID:
        await message.answer(BLOCKED_GROUP_ONLY)
        return

    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.answer(USAGE_BLOCK_USER)
        return

    user_id = int(args[1])
    block_minutes = int(args[2]) if len(args) == 3 and args[2].isdigit() else 60

    await redis_client.set(f"blocked:{user_id}", "1", ex=block_minutes * 60)
    logger.info(f"User {user_id} заблокирован на {block_minutes} минут (команда в группе {Config.GROUP_CHAT_ID})")
    await message.answer(BLOCK_USER_SUCCESS.format(user_id=user_id, minutes=block_minutes))

async def unblock_user_handler(message: types.Message):
    if message.chat.id != Config.GROUP_CHAT_ID:
        await message.answer(BLOCKED_GROUP_ONLY)
        return

    args = message.text.split()
    if len(args) != 2 or not args[1].isdigit():
        await message.answer(USAGE_UNBLOCK_USER)
        return

    user_id = int(args[1])
    await redis_client.delete(f"blocked:{user_id}")
    logger.info(f"User {user_id} разблокирован (команда в группе {Config.GROUP_CHAT_ID})")
    await message.answer(UNBLOCK_USER_SUCCESS.format(user_id=user_id))
