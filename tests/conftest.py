import pytest
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from src.bot import register_handlers

@pytest.fixture
def test_bot():
    return Bot(token="123456789:TEST_FAKE_TOKEN")

@pytest.fixture
def test_dispatcher(test_bot, mocker):
    mock_redis = mocker.patch("src.bot.redis_client")
    mock_redis.ping.return_value = True
    mock_redis.exists.return_value = False

    storage = MemoryStorage()
    dp = Dispatcher(storage=storage, bot=test_bot)
    register_handlers(dp)
    return dp
