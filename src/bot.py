from aiogram.filters import Command
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage

from src.utils.config import BOT_TOKEN
from src.handlers.start import start_handler
from src.handlers.callback import callback_handler
from src.handlers.feedback import feedback_message_handler
from src.handlers.admin_reply import admin_reply_text_handler  
from src.services.redis_client import redis_client

from aiogram.types import Message
from aiogram.filters import Filter

from src.utils.logger import setup_logger
logger = setup_logger(__name__)

storage = RedisStorage(redis=redis_client)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

class IsAdminReplying(Filter):
    async def __call__(self, message: Message) -> bool:
        result = await redis_client.exists(f"admin_replying:{message.from_user.id}")
        logger.info(f"IsAdminReplying filter: user_id={message.from_user.id} result={bool(result)}")
        return bool(result)

def register_handlers(dp: Dispatcher):
    dp.message.register(start_handler, Command(commands=["start"]))
    dp.callback_query.register(callback_handler)
    dp.message.register(admin_reply_text_handler, IsAdminReplying())
    dp.message.register(feedback_message_handler)
