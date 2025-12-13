import atexit
import signal
import subprocess
import sys
from os import environ
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import FrameType


def start_api() -> subprocess.Popen:
    return subprocess.Popen(  # noqa: S603
        [  # noqa: S607
            "uv",
            "run",
            "uvicorn",
            "petstore:app",
            "--host",
            "0.0.0.0",  # noqa: S104
            "--port",
            environ["PETSTORE_PORT"],
        ]
    )


def main() -> None:
    api_proc = start_api()
    atexit.register(lambda: api_proc.terminate())

    # Forward Docker stop signals
    def handle_signal(_signum: int, _frame: FrameType | None) -> None:
        api_proc.terminate()
        sys.exit(0)

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Wait for API to finish
    api_proc.wait()


if __name__ == "__main__":
    main()
