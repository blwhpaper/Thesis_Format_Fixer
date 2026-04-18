"""CLI entrypoint for thesis-format-fixer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from thesis_format_fixer.app.runner import run_check, run_fix


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="thesis-format-fixer")
    subparsers = parser.add_subparsers(dest="command")

    check_parser = subparsers.add_parser("check", help="Check a DOCX file")
    check_parser.add_argument("file", type=Path, help="Input DOCX path")

    fix_parser = subparsers.add_parser("fix", help="Fix a DOCX file")
    fix_parser.add_argument("file", type=Path, help="Input DOCX path")
    fix_parser.add_argument("--out", required=True, type=Path, help="Output DOCX path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        return run_check(args.file)

    if args.command == "fix":
        return run_fix(args.file, args.out)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
