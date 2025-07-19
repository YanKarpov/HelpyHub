import os
import redis.asyncio as redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_client = redis.Redis(
    host=REDIS_HOST,    
    port=REDIS_PORT,
    db=0,
    decode_responses=True
)

FEEDBACK_LOCK_KEY = "feedback_lock:{user_id}"
USER_STATE_KEY = "user_state:{user_id}"
FEEDBACK_TYPE_KEY = "feedback_type:{user_id}"

async def can_create_new_feedback(user_id: int) -> bool:
    key = FEEDBACK_LOCK_KEY.format(user_id=user_id)
    exists = await redis_client.exists(key)
    return not bool(exists)

async def lock_feedback(user_id: int):
    key = FEEDBACK_LOCK_KEY.format(user_id=user_id)
    await redis_client.set(key, "locked", ex=3600)

async def unlock_feedback(user_id: int):
    key = FEEDBACK_LOCK_KEY.format(user_id=user_id)
    await redis_client.delete(key)
