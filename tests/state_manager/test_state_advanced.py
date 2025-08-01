import pytest
from unittest.mock import AsyncMock, patch
from src.services.state_manager import StateManager

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_save_state_with_ttl_admin_replying_to_sets_key(mock_redis):
    sm = StateManager(user_id=42)
    await sm.save_state_with_ttl("admin_replying_to", "99", ttl=60)
    mock_redis.set.assert_awaited_once_with(sm.admin_replying_key, "99", ex=60)

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_save_state_with_ttl_other_field_calls_hset(mock_redis):
    sm = StateManager(user_id=42)
    await sm.save_state_with_ttl("field", "value", ttl=60)
    mock_redis.hset.assert_awaited_once_with(sm.state_key, "field", "value")

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_lock_and_unlock_user(mock_redis):
    sm = StateManager(user_id=42)
    await sm.lock_user(expire=120)
    mock_redis.set.assert_awaited_with(sm.lock_key, "1", ex=120)

    await sm.unlock_user()
    mock_redis.delete.assert_awaited_with(sm.lock_key)

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_can_create_feedback_returns_correct_boolean(mock_redis):
    sm = StateManager(user_id=42)
    mock_redis.exists.return_value = 0
    assert await sm.can_create_feedback() is True

    mock_redis.exists.return_value = 1
    assert await sm.can_create_feedback() is False

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_set_get_delete_feedback_type(mock_redis):
    sm = StateManager(user_id=42)
    await sm.set_feedback_type("bug", expire=300)
    mock_redis.set.assert_awaited_with(sm.feedback_type_key, "bug", ex=300)

    mock_redis.get.return_value = b"bug"
    val = await sm.get_feedback_type()
    assert val == "bug"

    await sm.delete_feedback_type()
    mock_redis.delete.assert_awaited_with(sm.feedback_type_key)

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_block_unblock_and_is_blocked(mock_redis):
    sm = StateManager(user_id=42)
    await sm.block_user(expire=3600)
    mock_redis.set.assert_awaited_with(sm.blocked_key, "1", ex=3600)

    await sm.unblock_user()
    mock_redis.delete.assert_awaited_with(sm.blocked_key)

    mock_redis.exists.return_value = 1
    assert await sm.is_blocked() is True

    mock_redis.exists.return_value = 0
    assert await sm.is_blocked() is False

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_set_and_get_admin_reply_target(mock_redis):
    sm = StateManager(user_id=42)
    await sm.set_admin_reply_target(99, expire=3600)
    mock_redis.set.assert_awaited_with(sm.admin_replying_key, "99", ex=3600)

    mock_redis.get.return_value = b"99"
    assert await sm.get_admin_reply_target() == 99

    mock_redis.get.return_value = None
    assert await sm.get_admin_reply_target() is None

def test_synonyms_point_to_correct_methods():
    sm = StateManager(user_id=42)
    assert sm.lock_feedback == sm.lock_user
    assert sm.unlock_feedback == sm.unlock_user
    assert sm.can_create_new == sm.can_create_feedback
    assert sm.can_create_new_feedback == sm.can_create_feedback
