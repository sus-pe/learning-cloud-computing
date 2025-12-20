from typing import TYPE_CHECKING

from petstore.store.redis import get_redis

if TYPE_CHECKING:
    from docker.models.containers import Container


async def test_redis(redis_container: Container) -> None:
    redis = get_redis()
    assert await redis.get("key") is None
    await redis.set("key", "value")
    assert await redis.get("key") == "value"
    assert redis_container.health.lower() == "healthy"
