from os import environ

from redis.asyncio import Redis


def get_redis() -> Redis:
    assert "REDIS_URL" in environ
    redis_url = environ["REDIS_URL"]
    assert redis_url
    return Redis.from_url(
        redis_url,
        decode_responses=True,
    )
