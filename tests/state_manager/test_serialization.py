import pytest
from src.services.state_manager import StateManager

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_value, expected_serialized",
    [
        (True, "true"),
        (False, "false"),
        ("string", "string"),
        (123, "123"),
        (None, "None"),  
    ],
)
async def test_serialize_value(input_value, expected_serialized):
    serialized = StateManager._serialize_value(input_value)
    assert serialized == expected_serialized

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "input_value, expected_deserialized",
    [
        ("true", True),
        ("false", False),
        ("string", "string"),
        ("123", "123"),
        (b"true", True),
        (b"false", False),
        (b"abc", "abc"),
    ],
)
async def test_deserialize_value(input_value, expected_deserialized):
    deserialized = StateManager._deserialize_value(input_value)
    assert deserialized == expected_deserialized
