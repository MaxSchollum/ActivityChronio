from aw_client import ActivityWatchClient
from aw_core.log import setup_logging

from .config import parse_args
from .watcher import ScreenshotWatcher


def main() -> None:
    args = parse_args()

    setup_logging(
        "aw-watcher-screenshot",
        testing=args.testing,
        verbose=args.verbose,
        log_stderr=True,
        log_file=True,
    )

    client = ActivityWatchClient(
        "aw-watcher-screenshot",
        host=args.host,
        port=args.port,
        testing=args.testing,
    )
    ScreenshotWatcher(client).run()


if __name__ == "__main__":
    main()
