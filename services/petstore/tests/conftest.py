from collections.abc import Generator
from pathlib import Path

import docker
import pytest
from docker import DockerClient
from dotenv import dotenv_values
from pytest import fixture

type DotEnv = dict[str, str | None]
type PersistentFixture[T] = Generator[T]

PETSTORE_PORT_ENV_KEY: str = "PETSTORE_PORT"
pytest.register_assert_rewrite("petstore.tester")


@fixture(scope="session")
def project_root() -> Path:
    expected = Path(__file__).resolve().parent.parent.parent.parent.resolve()
    assert expected.is_dir(), f"Expected project root to exist {expected!r}"
    return expected


@fixture(scope="session")
def petstore_root(project_root: Path) -> Path:
    expected = project_root / "services" / "petstore"
    assert expected.is_dir(), f"Expected petstore root directory to exist {expected!r}"
    return expected


@fixture(scope="session")
def dotenv_path(petstore_root: Path) -> Path:
    expected = petstore_root / ".env"
    assert expected.is_file(), f"Expected .env file to exist {expected!r}"
    return expected


@fixture(scope="session")
def dotenv(dotenv_path: Path) -> DotEnv:
    return dotenv_values(dotenv_path)


@fixture(scope="session")
def secret_ninja_api_key(dotenv: DotEnv) -> str:
    assert "NINJA_API_KEY" in dotenv
    key = dotenv["NINJA_API_KEY"]
    assert key
    return key


@fixture(scope="session")
def petstore_port(dotenv: DotEnv) -> int:
    assert PETSTORE_PORT_ENV_KEY in dotenv
    port = dotenv[PETSTORE_PORT_ENV_KEY]
    assert port
    return int(port)


@fixture(scope="session")
def petstore_base_url(petstore_port: int) -> str:
    return f"http://localhost:{petstore_port}"


@fixture(scope="session")
def docker_engine() -> DockerClient:
    return docker.from_env()


@fixture(scope="session")
def example_picture_path(petstore_root: Path) -> Path:
    expected = petstore_root / "tests" / "res" / "1.jamie.jpg"
    assert expected.is_file()
    return expected


@fixture(scope="session")
def example_picture_path2(petstore_root: Path) -> Path:
    expected = petstore_root / "tests" / "res" / "1.jamie_after_put.jpg"
    assert expected.is_file()
    return expected
