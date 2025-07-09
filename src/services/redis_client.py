import redis.asyncio as redis

redis_client = redis.Redis(
    host='localhost',    # адрес Redis-сервера
    port=6379,           # порт Redis (по умолчанию 6379)
    db=0,                # номер базы Redis
    decode_responses=True  # чтобы получать строки, а не байты
)

async def can_create_new_feedback(user_id: int) -> bool:
    key = f"feedback_lock:{user_id}"
    exists = await redis_client.exists(key)
    return not bool(exists)

async def lock_feedback(user_id: int):
    key = f"feedback_lock:{user_id}"
    await redis_client.set(key, "locked", ex=3600)

async def unlock_feedback(user_id: int):
    key = f"feedback_lock:{user_id}"
    await redis_client.delete(key)


