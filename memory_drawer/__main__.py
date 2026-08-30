"""Command line entry point: python -m memory_drawer."""

import argparse
import os
import shutil
from pathlib import Path

from memory_drawer import __version__
from memory_drawer.config import ConfigError, load_config


def _human_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    raise AssertionError("unreachable")


def _scan(source: Path) -> tuple[int, int]:
    """Count files and total bytes in a source, read-only."""
    count = 0
    total = 0
    for dirpath, dirnames, filenames in os.walk(source, followlinks=False):
        dirnames.sort()
        for name in sorted(filenames):
            try:
                total += os.path.getsize(Path(dirpath) / name)
            except OSError:
                continue
            count += 1
    return count, total


def run_consolidate(config_path: str, dry_run: bool) -> int:
    if not dry_run:
        print("copying is not implemented yet")
        return 1
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"config error: {exc}")
        return 1
    print(f"Config OK: {config.master}")
    grand_count = 0
    grand_total = 0
    for source in config.sources:
        count, total = _scan(source.path)
        grand_count += count
        grand_total += total
        print(f"  {source.id:<10} {str(source.path):<30} {count:>6} files, {_human_size(total)}")
    print(f"Total: {grand_count} files, {_human_size(grand_total)}")
    free = shutil.disk_usage(config.master).free
    label = f" on {config.master.drive}" if config.master.drive else ""
    status = (
        "OK"
        if free >= grand_total
        else (f"WARNING: less than the total source size ({_human_size(free)} free)")
    )
    print(f"Free space{label}: {_human_size(free)} ({status})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="memory_drawer",
        description="Consolidate scattered backups into one organized archive.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")
    consolidate = sub.add_parser(
        "consolidate", help="validate config and show the consolidation plan"
    )
    consolidate.add_argument(
        "--config", default="config.json", help="config file (default: config.json)"
    )
    consolidate.add_argument(
        "--dry-run",
        action="store_true",
        help="validate, scan sources and print the plan, touch nothing",
    )

    args = parser.parse_args(argv)
    if args.command == "consolidate":
        return run_consolidate(args.config, args.dry_run)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
