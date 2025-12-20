from typing import TYPE_CHECKING

from httpx import AsyncClient
from pytest import fixture

from petstore.store.docker import run_container
from petstore.store.tester import PetStoreContainerTester

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator
    from pathlib import Path

    from docker import DockerClient
    from docker.models.containers import Container

    from tests.conftest import DotEnv

from typing import Any

CONTAINER_NAME: str = "petstore-test-container"


@fixture(scope="session")
def dockerfile(project_root: Path) -> Path:
    expected = project_root / "petstore.Dockerfile"
    assert expected.is_file(), f"Expected petstore.Dockerfile to exist {expected!r}"
    return expected


@fixture(scope="package")
def _petstore_container(
    docker_engine: DockerClient, petstore_port: int, dockerfile: Path, dotenv: DotEnv
) -> Generator[Container, Any]:
    image = "petstore-test"
    docker_engine.images.build(
        path=str(dockerfile.parent), tag=image, rm=True, forcerm=True
    )

    yield from run_container(
        engine=docker_engine,
        image=image,
        name=CONTAINER_NAME,
        port=petstore_port,
        env=dotenv,
    )


@fixture
async def tester(
    _petstore_container: Container,
    petstore_base_url: str,
    example_picture_path: Path,
    example_picture_path2: Path,
) -> AsyncGenerator[PetStoreContainerTester, Any]:
    async with AsyncClient(base_url=petstore_base_url, timeout=2.0) as client:
        await client.post("/force-clear")
        yield PetStoreContainerTester(
            _petstore_container,
            client,
            example_picture_path,
            example_picture_path2=example_picture_path2,
        )
