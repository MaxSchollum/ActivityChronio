import argparse


def parse_args():
    parser = argparse.ArgumentParser(
        description="Capture local Chronio screenshots while ActivityWatch is not AFK."
    )
    parser.add_argument("--host", dest="host")
    parser.add_argument("--port", dest="port")
    parser.add_argument(
        "--testing", dest="testing", action="store_true", help="run in testing mode"
    )
    parser.add_argument(
        "--verbose",
        dest="verbose",
        action="store_true",
        help="run with verbose logging",
    )
    pause_group = parser.add_mutually_exclusive_group()
    pause_group.add_argument(
        "--pause",
        dest="pause",
        action="store_true",
        help="persist pause state and exit",
    )
    pause_group.add_argument(
        "--resume",
        dest="resume",
        action="store_true",
        help="clear persisted pause state and exit",
    )
    return parser.parse_args()
