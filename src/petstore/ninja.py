import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from json import JSONDecodeError
from typing import TYPE_CHECKING, Any

from httpx import AsyncClient, AsyncHTTPTransport, Response, Timeout

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class NinjaApiError(Exception):
    def __init__(self, response: Response) -> None:
        super().__init__()
        self.response = response


class NinjaAnimals:
    def __init__(self, ninja_api: AsyncClient) -> None:
        self.api = ninja_api

    @classmethod
    @asynccontextmanager
    async def session(cls, token: str) -> AsyncGenerator[NinjaAnimals]:
        timeout = Timeout(
            connect=20.0,  # DNS + TCP (critical for you)
            read=30.0,
            write=10.0,
            pool=5.0,
        )

        # Specifying this transport layer forces IPv4 usage, which greatly speeds
        # all operations between client and server (from seconds to milliseconds).
        transport = AsyncHTTPTransport(local_address="0.0.0.0")  # noqa: S104
        async with AsyncClient(
            base_url="https://api.api-ninjas.com/",
            headers={"X-Api-Key": token},
            timeout=timeout,
            transport=transport,
        ) as client:
            yield cls(client)

    async def get(self, name: str) -> list[dict]:
        response = await self.api.get("/v1/animals", params={"name": name})
        try:
            assert response.is_success
            return response.json()
        except (JSONDecodeError, AssertionError) as e:
            raise NinjaApiError(response=response) from e


async def get_ninja() -> AsyncGenerator[NinjaAnimals, Any]:
    key: str = os.environ.get("NINJA_API_KEY", "")
    assert key, "NINJA_API_KEY must be set"

    async with NinjaAnimals.session(key) as session:
        yield session
