from asyncio import create_subprocess_shell
from asyncio.subprocess import PIPE


async def test_compose() -> None:
    proc = await create_subprocess_shell(
        "docker compose up",
        stdout=PIPE,
        stderr=PIPE,
    )
    proc.kill()
    assert await proc.wait()
