"""Command line entry point: python -m memory_drawer."""

import argparse
import shutil
import sys

from memory_drawer import __version__
from memory_drawer.config import Config, ConfigError, load_config
from memory_drawer.consolidate import ConsolidateAbort, consolidate, scan
from memory_drawer.layout import MANIFEST


def _escape_control(text: str) -> str:
    """Make text console-safe by escaping control characters."""
    return "".join(f"\\x{ord(c):02x}" if ord(c) < 32 or ord(c) == 127 else c for c in text)


def _human_size(n: int) -> str:
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units[:-1]:
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n //= 1024
    return f"{n:.1f} TB"


def _drive_label(config: Config) -> str:
    drive = config.master.drive
    return f" on {drive}" if drive else ""


def _dry_run(config: Config) -> int:
    print(f"Config OK: {_escape_control(str(config.master))}")
    grand_count = 0
    grand_total = 0
    walk_errors = 0
    for source in config.sources:
        scanned = scan(source.path)
        grand_count += scanned.count
        grand_total += scanned.total
        walk_errors += scanned.errors
        print(
            f"  {source.id:<10} {_escape_control(str(source.path)):<30} {scanned.count:>6} files, "
            f"{_human_size(scanned.total)}"
        )
    if walk_errors:
        print(f"Warning: {walk_errors} directories could not be read")
    print(f"Total: {grand_count} files, {_human_size(grand_total)}")
    try:
        free = shutil.disk_usage(config.master).free
    except OSError:
        print("Free space: unknown (drive could not be read)")
        return 0
    status = (
        "OK"
        if free >= grand_total
        else (f"WARNING: less than the total source size ({_human_size(free)} free)")
    )
    print(f"Free space{_drive_label(config)}: {_human_size(free)} ({status})")
    return 0


def _real_run(config: Config) -> int:
    manifest_path = config.master / MANIFEST
    print(f"Config OK: {_escape_control(str(config.master))}")
    total = 0
    for source in config.sources:
        total += scan(source.path).total
    try:
        free = shutil.disk_usage(config.master).free
    except OSError:
        free = None
    if free is not None and free < total:
        print(
            f"Warning: free space{_drive_label(config)} ({_human_size(free)}) "
            f"is less than the total source size ({_human_size(total)})"
        )
    try:
        result = consolidate(config, manifest_path)
    except ConsolidateAbort as exc:
        print(f"aborted: {_escape_control(str(exc))}")
        return 1
    print(f"Copied: {result.copied} files, {_human_size(result.bytes_copied)}")
    print(f"Re-copied: {result.re_copied}")
    print(f"Already present: {result.already_present}")
    print(f"Skipped (symlinks and non-regular files): {result.skipped}")
    if result.kind_fixes:
        print(f"Kind corrections: {result.kind_fixes}")
    if result.walk_errors:
        print(f"Warning: {result.walk_errors} directories could not be read")
    for warning in result.warnings:
        print(f"Warning: {_escape_control(warning)}")
    for diff in result.case_diffs:
        print(f"Case-only sidecar match: {_escape_control(diff)}")
    print(f"Errors: {len(result.errors)}")
    for error in result.errors:
        print(f"error: {_escape_control(error)}")
    return 1 if result.errors else 0


def run_consolidate(config_path: str, dry_run: bool) -> int:
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        print(f"config error: {exc}")
        return 1
    if dry_run:
        return _dry_run(config)
    return _real_run(config)


def main(argv: list[str] | None = None) -> int:
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        prog="memory_drawer",
        description="Consolidate scattered backups into one organized archive.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command")
    consolidate_cmd = sub.add_parser("consolidate", help="copy sources into the master folder")
    consolidate_cmd.add_argument(
        "--config", default="config.json", help="config file (default: config.json)"
    )
    consolidate_cmd.add_argument(
        "--dry-run",
        action="store_true",
        help="validate, scan sources and print the plan, touch nothing",
    )

    args = parser.parse_args(argv)
    if args.command == "consolidate":
        try:
            return run_consolidate(args.config, args.dry_run)
        except KeyboardInterrupt:
            print("interrupted")
            return 130
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
