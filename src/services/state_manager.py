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

    async def can_create_new_feedback(self) -> bool:
        return await self.can_create_new()
    
    async def lock_feedback(self, expire: int = 3600):
        await self.lock(expire)
    
    async def unlock_feedback(self):
        await self.unlock()

    async def _get_user_state(self) -> dict:
        return await redis_client.hgetall(self.state_key) or {}

    async def _save_user_state(self, **kwargs):
        if kwargs:
            await redis_client.hset(self.state_key, mapping=kwargs)

    async def get_state(self) -> dict:
        return await self._get_user_state()

    async def save_state(self, **kwargs):
        filtered = {k: v for k, v in kwargs.items() if v is not None}
        if filtered:
            await self._save_user_state(**filtered)

    async def save_state_with_ttl(self, field: str, value: str, ttl: int):
        if field == "admin_replying_to":
            await redis_client.set(self.admin_replying_key, value, ex=ttl)
        else:
            await self._save_user_state(**{field: value})

    async def get_state_field(self, field: str):
        if field == "admin_replying_to":
            val = await redis_client.get(self.admin_replying_key)
            return val.decode() if isinstance(val, bytes) else val
        state = await self._get_user_state()
        return state.get(field)

    async def delete_state_field(self, field: str):
        if field == "admin_replying_to":
            await redis_client.delete(self.admin_replying_key)
        else:
            await redis_client.hdel(self.state_key, field)

    async def delete_state(self):
        await redis_client.delete(self.state_key)
        await redis_client.delete(self.admin_replying_key)

    async def set_feedback_type(self, feedback_type: str, expire: int = 300):
        await redis_client.set(self.feedback_type_key, feedback_type, ex=expire)

    async def get_feedback_type(self) -> str | None:
        val = await redis_client.get(self.feedback_type_key)
        if val:
            return val.decode() if isinstance(val, bytes) else val
        return None

    async def delete_feedback_type(self):
        await redis_client.delete(self.feedback_type_key)

    async def can_create_new(self) -> bool:
        exists = await redis_client.exists(self.lock_key)
        return not bool(exists)

    async def lock(self, expire: int = 3600):
        await redis_client.set(self.lock_key, "1", ex=expire)

    async def unlock(self):
        await redis_client.delete(self.lock_key)

    async def is_blocked(self) -> bool:
        return await redis_client.exists(self.blocked_key) == 1