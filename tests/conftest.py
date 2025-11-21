import contextlib
import time
from datetime import timedelta
from os import environ
from typing import TYPE_CHECKING

import docker
from docker import DockerClient
from dotenv import load_dotenv
from httpx import AsyncClient
from pytest import fixture
from pytest_asyncio import fixture as async_fixture

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from docker.models.containers import Container


class PetStoreTester:
    def __init__(self, container: Container, base_url: str) -> None:
        self.container: Container = container
        self.base_url: str = base_url
        self.min_status: int = 100
        self.max_status: int = 599

    def validate_status(self, status: int) -> bool:
        return self.min_status <= status <= self.max_status


CONTAINER_NAME: str = "petstore-test-container"
PETSTORE_PORT_ENV_KEY: str = "PETSTORE_PORT"


@fixture(scope="session", autouse=True)
def load_env() -> None:
    load_dotenv()


@fixture(scope="session")
def petstore_port() -> int:
    return int(environ[PETSTORE_PORT_ENV_KEY])


@fixture(scope="session")
def docker_client() -> DockerClient:
    return docker.from_env()


@fixture(scope="session")
def tester(docker_client: DockerClient, petstore_port: int) -> Iterator[PetStoreTester]:
    with contextlib.suppress(Exception):
        prev: Container = docker_client.containers.get(CONTAINER_NAME)
        prev.kill()
        prev.remove(force=True)

    docker_client.images.build(path=".", tag="petstore-test", rm=True, forcerm=True)

    container: Container = docker_client.containers.run(
        "petstore-test",
        detach=True,
        name=CONTAINER_NAME,
        remove=True,
        auto_remove=True,
        environment={PETSTORE_PORT_ENV_KEY: petstore_port},
        ports={f"{petstore_port}/tcp": petstore_port},
    )

    for _ in range(60):
        container.reload()
        match container.attrs["State"]["Health"]["Status"]:
            case "healthy":
                break
            case "unhealthy":
                msg = "Unhealthy container"
                raise RuntimeError(msg)
            case _:
                time.sleep(timedelta(milliseconds=100).total_seconds())
    else:
        msg = "Container did not become healthy"
        raise RuntimeError(msg)

    yield PetStoreTester(container, f"http://localhost:{petstore_port}")

    with contextlib.suppress(Exception):
        container.kill()


@async_fixture
async def client(tester: PetStoreTester) -> AsyncIterator[AsyncClient]:
    async with AsyncClient(base_url=tester.base_url, timeout=2.0) as c:
        yield c
