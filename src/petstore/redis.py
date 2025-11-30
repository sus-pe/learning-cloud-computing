from redis.asyncio import Redis


def get_redis() -> Redis:
    return Redis.from_url(
        "redis://localhost:6379/0",
        decode_responses=True,
    )
