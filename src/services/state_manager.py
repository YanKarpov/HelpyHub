from typing import Any, Dict, Optional, Union
import asyncio
from src.services.redis_client import redis_client

USER_STATE_KEY = "user_state:{user_id}"
FEEDBACK_TYPE_KEY = "feedback_type:{user_id}"
FEEDBACK_LOCK_KEY = "feedback_lock:{user_id}"
BLOCKED_USER_KEY = "blocked:{user_id}"
ADMIN_REPLYING_KEY = "admin_replying:{admin_id}"

class StateManager:
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.state_key = USER_STATE_KEY.format(user_id=user_id)
        self.feedback_type_key = FEEDBACK_TYPE_KEY.format(user_id=user_id)
        self.blocked_key = BLOCKED_USER_KEY.format(user_id=user_id)
        self.lock_key = FEEDBACK_LOCK_KEY.format(user_id=user_id)
        self.admin_replying_key = ADMIN_REPLYING_KEY.format(admin_id=user_id)

    # Основные методы работы с состоянием
    async def save_state(self, **kwargs) -> None:
        """Сохраняет состояние с автоматической сериализацией значений"""
        if not kwargs:
            return

        processed = {
            k: self._serialize_value(v) 
            for k, v in kwargs.items()
            if v is not None
        }
        
        await redis_client.hset(self.state_key, mapping=processed)

    async def save_state_with_ttl(self, field: str, value: str, ttl: int):
        """Сохраняет отдельное поле состояния с TTL"""
        if field == "admin_replying_to":
            await redis_client.set(self.admin_replying_key, value, ex=ttl)
        else:
            await redis_client.hset(self.state_key, field, self._serialize_value(value))

    async def get_state(self) -> Dict[str, Any]:
        """Возвращает полное состояние с десериализацией"""
        raw_state = await redis_client.hgetall(self.state_key) or {}
        return {
            k.decode() if isinstance(k, bytes) else k: 
            self._deserialize_value(v) 
            for k, v in raw_state.items()
        }

    async def get_state_field(self, field: str) -> Any:
        """Получает конкретное поле состояния с правильным типом"""
        if field == "admin_replying_to":
            val = await redis_client.get(self.admin_replying_key)
            return val.decode() if isinstance(val, bytes) else val
        
        value = await redis_client.hget(self.state_key, field)
        return self._deserialize_value(value) if value else None

    async def delete_state_field(self, field: str):
        """Удаляет конкретное поле из состояния"""
        if field == "admin_replying_to":
            await redis_client.delete(self.admin_replying_key)
        else:
            await redis_client.hdel(self.state_key, field)

    async def clear_state(self) -> None:
        """Полная очистка всех данных пользователя"""
        await asyncio.gather(
            redis_client.delete(self.state_key),
            redis_client.delete(self.feedback_type_key),
            redis_client.delete(self.lock_key),
            redis_client.delete(self.admin_replying_key),
            redis_client.delete(self.blocked_key)
        )

    # Методы для работы с feedback
    async def set_feedback_type(self, feedback_type: str, expire: int = 300):
        await redis_client.set(self.feedback_type_key, feedback_type, ex=expire)

    async def get_feedback_type(self) -> Optional[str]:
        val = await redis_client.get(self.feedback_type_key)
        return val.decode() if isinstance(val, bytes) else val

    async def delete_feedback_type(self):
        await redis_client.delete(self.feedback_type_key)

    # Методы блокировки/разблокировки
    async def lock_user(self, expire: int = 3600) -> None:
        await redis_client.set(self.lock_key, "1", ex=expire)

    async def unlock_user(self) -> None:
        await redis_client.delete(self.lock_key)

    async def can_create_feedback(self) -> bool:
        return not await redis_client.exists(self.lock_key)

    # Методы блокировки пользователя
    async def block_user(self, expire: int = None) -> None:
        if expire:
            await redis_client.set(self.blocked_key, "1", ex=expire)
        else:
            await redis_client.set(self.blocked_key, "1")

    async def unblock_user(self) -> None:
        await redis_client.delete(self.blocked_key)

    async def is_blocked(self) -> bool:
        return await redis_client.exists(self.blocked_key) == 1

    # Методы для работы с админскими ответами
    async def set_admin_reply_target(self, target_user_id: int, expire: int = 3600) -> None:
        await redis_client.set(self.admin_replying_key, str(target_user_id), ex=expire)

    async def get_admin_reply_target(self) -> Optional[int]:
        target = await redis_client.get(self.admin_replying_key)
        return int(target) if target else None

    # Синонимы для совместимости
    lock_feedback = lock_user
    unlock_feedback = unlock_user
    can_create_new = can_create_feedback
    can_create_new_feedback = can_create_feedback

    @staticmethod
    def _serialize_value(value: Any) -> str:
        """Конвертирует значения для хранения в Redis"""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @staticmethod 
    def _deserialize_value(value: Union[str, bytes]) -> Any:
        """Восстанавливает оригинальные типы данных"""
        if isinstance(value, bytes):
            value = value.decode()
        
        if value == "true":
            return True
        elif value == "false":
            return False
        return value