from _pytest.fixtures import fixture
from dotenv import dotenv_values

type DotEnv = dict[str, str | None]


@fixture(scope="session")
def dotenv() -> DotEnv:
    return dotenv_values()
