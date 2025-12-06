import atexit
import signal
import subprocess
import sys
import time
from os import environ
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import FrameType


def start_redis() -> subprocess.Popen:
    return subprocess.Popen(
        ["redis-server"],  # noqa: S607
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def start_api() -> subprocess.Popen:
    return subprocess.Popen(  # noqa: S603
        [  # noqa: S607
            "uv",
            "run",
            "uvicorn",
            "petstore_catalog-catalog:app",
            "--host",
            "0.0.0.0",  # noqa: S104
            "--port",
            environ["PETSTORE_PORT"],
        ]
    )


def main() -> None:
    redis_proc = start_redis()

    # Ensure Redis shuts down if container stops
    atexit.register(lambda: redis_proc.terminate())

    # Give Redis a moment to boot
    time.sleep(0.5)

    api_proc = start_api()
    atexit.register(lambda: api_proc.terminate())

    # Forward Docker stop signals
    def handle_signal(_signum: int, _frame: FrameType | None) -> None:
        api_proc.terminate()
        redis_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Wait for API to finish
    api_proc.wait()


if __name__ == "__main__":
    main()
