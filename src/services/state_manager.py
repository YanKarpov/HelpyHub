import logging
from typing import Any, Dict, Optional, Union
import asyncio
from src.services.redis_client import redis_client
from src.utils.logger import setup_logger  

USER_STATE_KEY = "user_state:{user_id}"
FEEDBACK_TYPE_KEY = "feedback_type:{user_id}"
FEEDBACK_LOCK_KEY = "feedback_lock:{user_id}"
BLOCKED_USER_KEY = "blocked:{user_id}"
ADMIN_REPLYING_KEY = "admin_replying:{admin_id}"

class StateManager:
    
    def __init__(self, user_id: int, logger: Optional[logging.Logger] = None):
        self.user_id = user_id
        self.state_key = USER_STATE_KEY.format(user_id=user_id)
        self.feedback_type_key = FEEDBACK_TYPE_KEY.format(user_id=user_id)
        self.blocked_key = BLOCKED_USER_KEY.format(user_id=user_id)
        self.lock_key = FEEDBACK_LOCK_KEY.format(user_id=user_id)
        self.admin_replying_key = ADMIN_REPLYING_KEY.format(admin_id=user_id)
        self.logger = logger or setup_logger(__name__)

    # Основные методы работы с состоянием
    async def save_state(self, **kwargs) -> None:
        if not kwargs:
            return

        processed = {
            k: self._serialize_value(v) 
            for k, v in kwargs.items()
            if v is not None
        }

        await redis_client.hset(self.state_key, mapping=processed)

        # Формируем сокращённый лог
        simple_processed = {}
        for k, v in processed.items():
            if isinstance(v, str) and len(v) > 100:
                simple_processed[k] = f"<long string, length={len(v)}>"
            else:
                simple_processed[k] = v

        self.logger.info(f"[User {self.user_id}] save_state: {simple_processed}")


    async def get_state(self) -> Dict[str, Any]:
        raw_state = await redis_client.hgetall(self.state_key) or {}
        state = {
            k.decode() if isinstance(k, bytes) else k: 
            self._deserialize_value(v) 
            for k, v in raw_state.items()
        }
        
        # Для логирования: убираем детали, если значение — длинная строка (например JSON)
        simple_state = {}
        for k, v in state.items():
            if isinstance(v, str) and len(v) > 100:
                simple_state[k] = f"<long string, length={len(v)}>"
            else:
                simple_state[k] = v

        self.logger.info(f"[User {self.user_id}] get_state: {simple_state}")
        return state

    async def get_state_field(self, field: str) -> Any:
        if field == "admin_replying_to":
            val = await redis_client.get(self.admin_replying_key)
            val_decoded = val.decode() if isinstance(val, bytes) else val
            self.logger.info(f"[User {self.user_id}] get_state_field: {field} = {val_decoded}")
            return val_decoded
        
        value = await redis_client.hget(self.state_key, field)
        deserialized = self._deserialize_value(value) if value else None
        self.logger.info(f"[User {self.user_id}] get_state_field: {field} = {deserialized}")
        return deserialized

    async def delete_state_field(self, field: str):
        if field == "admin_replying_to":
            await redis_client.delete(self.admin_replying_key)
        else:
            await redis_client.hdel(self.state_key, field)
        self.logger.info(f"[User {self.user_id}] delete_state_field: {field}")

    async def clear_state(self) -> None:
        await asyncio.gather(
            redis_client.delete(self.state_key),
            redis_client.delete(self.feedback_type_key),
            # redis_client.delete(self.lock_key),
            redis_client.delete(self.admin_replying_key),
            redis_client.delete(self.blocked_key)
        )
        self.logger.info(f"[User {self.user_id}] clear_state called")

    # Методы для работы с feedback
    async def set_feedback_type(self, feedback_type: str, expire: int = 300):
        await redis_client.set(self.feedback_type_key, feedback_type, ex=expire)
        self.logger.info(f"[User {self.user_id}] set_feedback_type: {feedback_type} (expire={expire})")

    async def get_feedback_type(self) -> Optional[str]:
        val = await redis_client.get(self.feedback_type_key)
        decoded = val.decode() if isinstance(val, bytes) else val
        self.logger.info(f"[User {self.user_id}] get_feedback_type: {decoded}")
        return decoded

    async def delete_feedback_type(self):
        await redis_client.delete(self.feedback_type_key)
        self.logger.info(f"[User {self.user_id}] delete_feedback_type")

    # Методы блокировки/разблокировки
    async def lock_user(self, expire: int = 3600) -> None:
        result = await redis_client.set(self.lock_key, "1", ex=expire)
        self.logger.info(f"[User {self.user_id}] lock_user set lock_key with expire {expire}, result: {result}")

    async def unlock_user(self) -> None:
        await redis_client.delete(self.lock_key)
        self.logger.info(f"[User {self.user_id}] unlock_user deleted lock_key")

    async def can_create_feedback(self) -> bool:
        exists = await redis_client.exists(self.lock_key)
        can_create = exists == 0
        self.logger.info(f"[User {self.user_id}] can_create_feedback: lock_key exists={exists}, can_create={can_create}")
        return can_create

    # Методы блокировки пользователя
    async def block_user(self, expire: int = None) -> None:
        if expire:
            await redis_client.set(self.blocked_key, "1", ex=expire)
            self.logger.info(f"[User {self.user_id}] block_user with expire {expire}")
        else:
            await redis_client.set(self.blocked_key, "1")
            self.logger.info(f"[User {self.user_id}] block_user without expire")

    async def unblock_user(self) -> None:
        await redis_client.delete(self.blocked_key)
        self.logger.info(f"[User {self.user_id}] unblock_user")

    async def is_blocked(self) -> bool:
        exists = await redis_client.exists(self.blocked_key)
        blocked = exists == 1
        self.logger.info(f"[User {self.user_id}] is_blocked: {blocked}")
        return blocked

    # Методы для работы с админскими ответами
    async def set_admin_reply_target(self, target_user_id: int, expire: int = 3600) -> None:
        await redis_client.set(self.admin_replying_key, str(target_user_id), ex=expire)
        self.logger.info(f"[User {self.user_id}] set_admin_reply_target: {target_user_id} (expire={expire})")

    async def get_admin_reply_target(self) -> Optional[int]:
        target = await redis_client.get(self.admin_replying_key)
        if target:
            target_int = int(target)
            self.logger.info(f"[User {self.user_id}] get_admin_reply_target: {target_int}")
            return target_int
        self.logger.info(f"[User {self.user_id}] get_admin_reply_target: None")
        return None

    # Синонимы для совместимости
    lock_feedback = lock_user
    unlock_feedback = unlock_user
    can_create_new = can_create_feedback
    can_create_new_feedback = can_create_feedback

    @staticmethod
    def _serialize_value(value: Any) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @staticmethod 
    def _deserialize_value(value: Union[str, bytes]) -> Any:
        if isinstance(value, bytes):
            value = value.decode()
        
        if value == "true":
            return True
        elif value == "false":
            return False
        return value
