"""CLI entrypoint for thesis-format-fixer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from thesis_format_fixer.app.runner import run_batch_fix, run_check, run_fix


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="thesis-format-fixer")
    subparsers = parser.add_subparsers(dest="command")

    check_parser = subparsers.add_parser("check", help="Check a DOCX file")
    check_parser.add_argument("file", type=Path, help="Input DOCX path")
    check_parser.add_argument("--report-json", type=Path, help="Output report JSON path")
    check_parser.add_argument("--report-md", type=Path, help="Output report Markdown path")

    fix_parser = subparsers.add_parser("fix", help="Fix a DOCX file")
    fix_parser.add_argument("file", type=Path, help="Input DOCX path")
    fix_parser.add_argument("--out", required=True, type=Path, help="Output DOCX path")
    fix_parser.add_argument("--report-json", type=Path, help="Output report JSON path")
    fix_parser.add_argument("--report-md", type=Path, help="Output report Markdown path")

    batch_parser = subparsers.add_parser("batch-fix", help="Batch fix DOCX files in a directory")
    batch_parser.add_argument("dir", type=Path, help="Input directory containing DOCX files")
    batch_parser.add_argument("--out-dir", required=True, type=Path, help="Batch output directory")
    batch_parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Disable recursive scan (default is recursive)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        return run_check(args.file, report_json_out=args.report_json, report_md_out=args.report_md)

    if args.command == "fix":
        return run_fix(
            args.file,
            args.out,
            report_json_out=args.report_json,
            report_md_out=args.report_md,
        )

    if args.command == "batch-fix":
        return run_batch_fix(args.dir, args.out_dir, recursive=not args.no_recursive)

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
