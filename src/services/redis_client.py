import redis.asyncio as redis

redis_client = redis.Redis(
    host='localhost',    # адрес Redis-сервера
    port=6379,           # порт Redis (по умолчанию 6379)
    db=0,                # номер базы Redis
    decode_responses=True  # чтобы получать строки, а не байты
)
