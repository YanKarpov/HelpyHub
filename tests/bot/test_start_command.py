import pytest
from aiogram.types import Message, User, Chat, Update
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_start_command(test_dispatcher, test_bot, mocker):
    # Мокаем все вызовы API
    mock_call = mocker.patch("aiogram.client.bot.Bot.__call__", new_callable=AsyncMock)

    message = Message(
        message_id=1,
        from_user=User(id=123, is_bot=False, first_name="Test"),
        chat=Chat(id=123, type="private"),
        date=0,
        text="/start"
    )
    update = Update(update_id=1, message=message)

    await test_dispatcher.feed_update(bot=test_bot, update=update)

    # Проверяем, что бот пытался что-то отправить
    mock_call.assert_called()
