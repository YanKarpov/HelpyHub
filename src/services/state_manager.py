import logging
from typing import Any, Dict, Optional, Union
import asyncio
import json
from src.services.redis_client import redis_client
from src.utils.logger import setup_logger  

# Redis ключи
USER_STATE_KEY = "user_state:{user_id}"
FEEDBACK_TYPE_KEY = "feedback_type:{user_id}"
FEEDBACK_LOCK_KEY = "feedback_lock:{user_id}"
BLOCKED_USER_KEY = "blocked:{user_id}"
ADMIN_REPLYING_KEY = "admin_replying:{admin_id}"
NAV_STACK_KEY = "nav_stack:{user_id}"  


class StateManager:
    """
    Управление состоянием пользователя, процессами обратной связи, блокировками, навигацией и админ-ответами.

    Использует Redis как хранилище состояния.
    """

    def __init__(self, user_id: int, logger: Optional[logging.Logger] = None):
        self.user_id = user_id
        self.state_key = USER_STATE_KEY.format(user_id=user_id)
        self.feedback_type_key = FEEDBACK_TYPE_KEY.format(user_id=user_id)
        self.blocked_key = BLOCKED_USER_KEY.format(user_id=user_id)
        self.lock_key = FEEDBACK_LOCK_KEY.format(user_id=user_id)
        self.admin_replying_key = ADMIN_REPLYING_KEY.format(admin_id=user_id)
        self.nav_stack_key = NAV_STACK_KEY.format(user_id=user_id)
        self.logger = logger or setup_logger(__name__)

    # Общие методы состояния

    async def save_state(self, **kwargs) -> None:
        """
        Сохраняет состояние пользователя в Redis.

        Значения сериализуются в строки. None значения игнорируются.
        """
        if not kwargs:
            return

        processed = {k: self._serialize_value(v) for k, v in kwargs.items() if v is not None}
        await redis_client.hset(self.state_key, mapping=processed)

        simple_processed = {
            k: (f"<long string, length={len(v)}>" if isinstance(v, str) and len(v) > 100 else v)
            for k, v in processed.items()
        }
        self.logger.info(f"[User {self.user_id}] save_state: {simple_processed}")

    async def get_state(self) -> Dict[str, Any]:
        """
        Получает все сохраненные поля состояния пользователя из Redis.
        """
        raw_state = await redis_client.hgetall(self.state_key) or {}
        state = {
            k.decode() if isinstance(k, bytes) else k: self._deserialize_value(v)
            for k, v in raw_state.items()
        }

        simple_state = {
            k: (f"<long string, length={len(v)}>" if isinstance(v, str) and len(v) > 100 else v)
            for k, v in state.items()
        }
        self.logger.info(f"[User {self.user_id}] get_state: {simple_state}")
        return state

    async def get_state_field(self, field: str) -> Any:
        """
        Получить конкретное поле состояния пользователя.
        Специальная обработка для admin_replying_to.
        """
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
        """
        Удаляет конкретное поле состояния пользователя.
        """
        if field == "admin_replying_to":
            await redis_client.delete(self.admin_replying_key)
        else:
            await redis_client.hdel(self.state_key, field)
        self.logger.info(f"[User {self.user_id}] delete_state_field: {field}")

    async def clear_state(self) -> None:
        """
        Полностью очищает состояние пользователя, блокировки и feedback.
        """
        await asyncio.gather(
            redis_client.delete(self.state_key),
            redis_client.delete(self.feedback_type_key),
            redis_client.delete(self.admin_replying_key),
            redis_client.delete(self.blocked_key)
        )
        self.logger.info(f"[User {self.user_id}] clear_state called")

    # Feedback / блокировки

    async def set_feedback_type(self, feedback_type: str, expire: int = 300):
        """Сохраняет тип обратной связи с временем жизни в секундах."""
        await redis_client.set(self.feedback_type_key, feedback_type, ex=expire)
        self.logger.info(f"[User {self.user_id}] set_feedback_type: {feedback_type} (expire={expire})")

    async def get_feedback_type(self) -> Optional[str]:
        """Получить текущий тип обратной связи."""
        val = await redis_client.get(self.feedback_type_key)
        decoded = val.decode() if isinstance(val, bytes) else val
        self.logger.info(f"[User {self.user_id}] get_feedback_type: {decoded}")
        return decoded

    async def delete_feedback_type(self):
        """Удаляет тип обратной связи."""
        await redis_client.delete(self.feedback_type_key)
        self.logger.info(f"[User {self.user_id}] delete_feedback_type")

    async def lock_user(self, expire: int = 3600) -> None:
        """Устанавливает блокировку пользователя для создания feedback."""
        result = await redis_client.set(self.lock_key, "1", ex=expire)
        self.logger.info(f"[User {self.user_id}] lock_user expire={expire}, result: {result}")

    async def unlock_user(self) -> None:
        """Снимает блокировку пользователя."""
        await redis_client.delete(self.lock_key)
        self.logger.info(f"[User {self.user_id}] unlock_user")

    async def can_create_feedback(self) -> bool:
        """Проверяет, может ли пользователь создать новый feedback."""
        exists = await redis_client.exists(self.lock_key)
        can_create = exists == 0
        self.logger.info(f"[User {self.user_id}] can_create_feedback: {can_create}")
        return can_create

    async def block_user(self, expire: int = None) -> None:
        """Блокирует пользователя на опциональное время."""
        if expire:
            await redis_client.set(self.blocked_key, "1", ex=expire)
        else:
            await redis_client.set(self.blocked_key, "1")
        self.logger.info(f"[User {self.user_id}] block_user expire={expire}")

    async def unblock_user(self) -> None:
        """Разблокирует пользователя."""
        await redis_client.delete(self.blocked_key)
        self.logger.info(f"[User {self.user_id}] unblock_user")

    async def is_blocked(self) -> bool:
        """Проверяет, заблокирован ли пользователь."""
        exists = await redis_client.exists(self.blocked_key)
        blocked = exists == 1
        self.logger.info(f"[User {self.user_id}] is_blocked: {blocked}")
        return blocked

    # Админ-ответы

    async def set_admin_reply_target(self, target_user_id: int, expire: int = 3600) -> None:
        """Устанавливает текущую цель для ответа админа."""
        await redis_client.set(self.admin_replying_key, str(target_user_id), ex=expire)
        self.logger.info(f"[User {self.user_id}] set_admin_reply_target: {target_user_id} (expire={expire})")

    async def get_admin_reply_target(self) -> Optional[int]:
        """Возвращает ID пользователя, которому сейчас отвечает админ."""
        target = await redis_client.get(self.admin_replying_key)
        return int(target) if target else None

    # Навигация

    async def _read_nav_stack(self):
        """Читает стек навигации пользователя из Redis."""
        raw = await redis_client.get(self.nav_stack_key)
        if not raw:
            return [{"screen": "main", "params": {}}]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return [{"screen": "main", "params": {}}]

    async def _write_nav_stack(self, stack):
        """Сохраняет стек навигации пользователя в Redis."""
        await redis_client.set(self.nav_stack_key, json.dumps(stack))

    async def reset_nav(self):
        """Сбрасывает стек навигации к главному экрану."""
        await self._write_nav_stack([{"screen": "main", "params": {}}])
        self.logger.info(f"[User {self.user_id}] reset_nav -> main")

    async def clear_nav(self):
        """Полностью очищает навигацию пользователя."""
        await redis_client.delete(self.nav_stack_key)
        self.logger.info(f"[User {self.user_id}] clear_nav")

    async def push_nav(self, screen: str, params: dict = None):
        """Добавляет новый экран в стек навигации."""
        stack = await self._read_nav_stack()
        stack.append({"screen": screen, "params": params or {}})
        await self._write_nav_stack(stack)
        self.logger.info(f"[User {self.user_id}] push_nav -> {screen} {params}")

    async def pop_nav(self):
        """Удаляет последний экран из стека и возвращает предыдущий."""
        stack = await self._read_nav_stack()
        if len(stack) <= 1:
            return stack[0]
        stack.pop()
        await self._write_nav_stack(stack)
        self.logger.info(f"[User {self.user_id}] pop_nav -> {stack[-1]}")
        return stack[-1]

    async def go_back(self):
        """Возвращается на предыдущий экран (для кнопки Назад)."""
        prev = await self.pop_nav()
        return prev["screen"], prev["params"]

    async def goto_nav(self, screen: str, params: dict = None):
        """Перейти на конкретный экран, обрезая стек до этого экрана."""
        stack = await self._read_nav_stack()
        for i, entry in enumerate(stack):
            if entry["screen"] == screen:
                stack = stack[:i+1]
                if params is not None:
                    stack[-1]["params"] = params
                await self._write_nav_stack(stack)
                self.logger.info(f"[User {self.user_id}] goto_nav -> {screen} {params}")
                return
        await self.push_nav(screen, params)

    async def current_nav(self):
        """Возвращает текущий экран."""
        stack = await self._read_nav_stack()
        return stack[-1]

    async def get_nav_stack(self):
        """Возвращает полный стек навигации."""
        return await self._read_nav_stack()

    # Состояние обратной связи

    async def clear_feedback_state(self):
        """Сбрасывает состояние, связанное с процессом обратной связи."""
        await self.delete_state_field("prompt_message_id")
        await self.delete_state_field("type")
        await self.delete_state_field("is_named")
        await self.delete_feedback_type()
        await self.unlock_user()
        self.logger.info(f"[User {self.user_id}] clear_feedback_state called")


    # Алиасы

    lock_feedback = lock_user
    unlock_feedback = unlock_user
    can_create_new = can_create_feedback
    can_create_new_feedback = can_create_feedback

    # Вспомогательные методы

    @staticmethod
    def _serialize_value(value: Any) -> str:
        """Сериализация значения для хранения в Redis."""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    @staticmethod
    def _deserialize_value(value: Union[str, bytes]) -> Any:
        """Десериализация значения из Redis."""
        if isinstance(value, bytes):
            value = value.decode()
        if value == "true":
            return True
        if value == "false":
            return False
        return value
