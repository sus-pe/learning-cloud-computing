from contextlib import suppress
from datetime import timedelta
from time import sleep
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    from docker import DockerClient
    from docker.models.containers import Container


def run_container(  # noqa: PLR0913
    engine: DockerClient,
    image: str,
    name: str,
    port: int,
    env: dict[str, str | None] | None = None,
    healthcheck: dict | None = None,
) -> Generator[Container]:
    if not env:
        env = {}

    with suppress(Exception):
        prev: Container = engine.containers.get(name)
        prev.kill()
        prev.remove(force=True)

    container: Container = engine.containers.run(
        image=image,
        detach=True,
        name=name,
        remove=True,
        auto_remove=True,
        environment=env,
        ports={f"{port}/tcp": port},
        healthcheck=healthcheck,
    )

    for _ in range(60):
        container.reload()
        state = container.attrs["State"]
        if "Health" in state:
            match container.attrs["State"]["Health"]["Status"]:
                case "healthy":
                    break
                case "unhealthy":
                    msg = "Unhealthy container"
                    raise RuntimeError(msg)
                case _:
                    sleep(timedelta(milliseconds=100).total_seconds())
        else:
            msg = "Can't tell if container is healthy"
            raise RuntimeError(msg)

    else:
        msg = "Container did not become healthy"
        raise RuntimeError(msg)

    try:
        yield container
    finally:
        with suppress(Exception):
            container.kill()
