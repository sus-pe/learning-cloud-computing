from typing import TYPE_CHECKING, Any

from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient
from petstore import NinjaAnimals, app, get_redis
from petstore.docker import run_container
from petstore.tester import PetStoreTester

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from pathlib import Path

    from docker import DockerClient
    from docker.models.containers import Container

    from services.petstore.tests.conftest import PersistentFixture

from pytest import fixture


@fixture
async def ninja(secret_ninja_api_key: str) -> AsyncGenerator[NinjaAnimals, Any]:
    async with NinjaAnimals.session(secret_ninja_api_key) as session:
        yield session


@fixture(scope="package")
def redis_container(docker_engine: DockerClient) -> PersistentFixture[Container]:
    yield from run_container(
        engine=docker_engine,
        image="redis",
        name="redis-container",
        port=6379,
        healthcheck={
            "test": ["CMD", "redis-cli", "ping"],
            "interval": 5_000_000_000,  # 5 seconds in nanoseconds
            "timeout": 2_000_000_000,  # 2 seconds
            "retries": 5,
            "start_period": 5_000_000_000,  # 5 seconds
        },
    )


@fixture
async def petstore_server(
    petstore_base_url: str, dotenv_path: Path
) -> AsyncGenerator[AsyncClient]:
    # The Server expects some environment variables to be set.
    load_dotenv(dotenv_path)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url=petstore_base_url) as client:
        yield client


@fixture
async def tester(
    petstore_server: AsyncClient,
    redis_container: Container,  # noqa: ARG001
    example_picture_path: Path,
    example_picture_path2: Path,
) -> PetStoreTester:
    # Refresh the persistent shared fixture that is redis.
    redis = get_redis()
    await redis.flushall()
    return PetStoreTester(
        petstore_server,
        example_picture_path=example_picture_path,
        example_picture_path2=example_picture_path2,
    )
