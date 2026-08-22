"""Command line entry point: python -m memory_drawer."""

import argparse

from memory_drawer import __version__


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="memory_drawer",
        description="Organize a personal photo archive without ever deleting anything.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.parse_args(argv)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
