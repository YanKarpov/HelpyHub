import pytest
from unittest.mock import AsyncMock, patch
from src.services.state_manager import StateManager

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_save_state_hset_called(mock_redis):
    sm = StateManager(user_id=123)
    await sm.save_state(foo="bar", count=5, flag=True, none_val=None)
    
    expected_mapping = {
        "foo": "bar",
        "count": "5",
        "flag": "true"
    }
    mock_redis.hset.assert_awaited_once_with(sm.state_key, mapping=expected_mapping)

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_get_state_returns_deserialized(mock_redis):
    sm = StateManager(user_id=123)
    mock_redis.hgetall.return_value = {
        b"foo": b"bar",
        b"flag": b"true",
        b"count": b"10"
    }
    
    state = await sm.get_state()
    
    assert state == {
        "foo": "bar",
        "flag": True,
        "count": "10"
    }
    mock_redis.hgetall.assert_awaited_once_with(sm.state_key)

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_get_state_field_admin_replying_to(mock_redis):
    sm = StateManager(user_id=123)
    mock_redis.get.return_value = b"456"
    
    value = await sm.get_state_field("admin_replying_to")
    
    assert value == "456"
    mock_redis.get.assert_awaited_once_with(sm.admin_replying_key)

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_get_state_field_normal_field(mock_redis):
    sm = StateManager(user_id=123)
    mock_redis.hget.return_value = b"true"
    
    value = await sm.get_state_field("flag")
    
    assert value is True
    mock_redis.hget.assert_awaited_once_with(sm.state_key, "flag")

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_delete_state_field_admin_replying_to(mock_redis):
    sm = StateManager(user_id=123)
    await sm.delete_state_field("admin_replying_to")
    mock_redis.delete.assert_awaited_once_with(sm.admin_replying_key)

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_delete_state_field_normal(mock_redis):
    sm = StateManager(user_id=123)
    await sm.delete_state_field("foo")
    mock_redis.hdel.assert_awaited_once_with(sm.state_key, "foo")

@pytest.mark.asyncio
@patch("src.services.state_manager.redis_client", new_callable=AsyncMock)
async def test_clear_state_calls_delete_all(mock_redis):
    sm = StateManager(user_id=123)
    await sm.clear_state()
    
    mock_redis.delete.assert_awaited()
    expected_calls = {
        sm.state_key,
        sm.feedback_type_key,
        sm.lock_key,
        sm.admin_replying_key,
        sm.blocked_key
    }
    
    called_args = {call.args[0] for call in mock_redis.delete.await_args_list}
    assert expected_calls == called_args
