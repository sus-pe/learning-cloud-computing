from typing import TYPE_CHECKING, Any

from httpx import AsyncClient
from pytest_asyncio import fixture

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from tests.conftest import DotEnv


@fixture(scope="session")
def secret_ninja_api_key(dotenv: DotEnv) -> str:
    assert "NINJA_API_KEY" in dotenv
    key = dotenv["NINJA_API_KEY"]
    assert key
    return key


@fixture
async def ninja_client(secret_ninja_api_key: str) -> AsyncGenerator[AsyncClient, Any]:
    async with AsyncClient(
        base_url="https://api.api-ninjas.com/",
        headers={"X-Api-Key": secret_ninja_api_key},
    ) as client:
        yield client
