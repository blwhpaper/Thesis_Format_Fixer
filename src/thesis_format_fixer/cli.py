"""CLI entrypoint for thesis-format-fixer."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from thesis_format_fixer.app.runner import run_batch_fix, run_check, run_fix


def _add_review_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--review-mode",
        choices=("off", "basic", "llm"),
        default="off",
        help="V2 review mode: off (default), basic(rule-engine), llm(local model assisted)",
    )
    parser.add_argument(
        "--review-target",
        default="headings,references,pagination,body_english_punctuation",
        help="Comma separated review targets: headings,references,pagination,body_english_punctuation",
    )
    parser.add_argument(
        "--review-local-model",
        type=str,
        help="Local model name for --review-mode llm",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="thesis-format-fixer")
    subparsers = parser.add_subparsers(dest="command")

    check_parser = subparsers.add_parser("check", help="Check a DOCX file")
    check_parser.add_argument("file", type=Path, help="Input DOCX path")
    check_parser.add_argument("--report-json", type=Path, help="Output report JSON path")
    check_parser.add_argument("--report-md", type=Path, help="Output report Markdown path")
    check_parser.add_argument("--profile", type=Path, help="Profile YAML path for check-time drift audit")
    _add_review_options(check_parser)

    fix_parser = subparsers.add_parser("fix", help="Fix a DOCX file")
    fix_parser.add_argument("file", type=Path, help="Input DOCX path")
    fix_parser.add_argument("--out", required=True, type=Path, help="Output DOCX path")
    fix_parser.add_argument("--report-json", type=Path, help="Output report JSON path")
    fix_parser.add_argument("--report-md", type=Path, help="Output report Markdown path")
    _add_review_options(fix_parser)

    batch_parser = subparsers.add_parser("batch-fix", help="Batch fix DOCX files in a directory")
    batch_parser.add_argument("dir", type=Path, help="Input directory containing DOCX files")
    batch_parser.add_argument("--out-dir", required=True, type=Path, help="Batch output directory")
    batch_parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Disable recursive scan (default is recursive)",
    )
    _add_review_options(batch_parser)

    cli_review_parser = subparsers.add_parser("review", help="Review a DOCX file with findings JSON")
    cli_review_parser.add_argument("--input", required=True, type=Path, help="Input DOCX path")
    cli_review_parser.add_argument("--findings", required=True, type=Path, help="Input findings JSON path")
    cli_review_parser.add_argument("--output", required=True, type=Path, help="Output DOCX path")
    cli_review_parser.add_argument("--report", required=True, type=Path, help="Output report JSON path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "check":
        return run_check(
            args.file,
            profile_path=args.profile,
            report_json_out=args.report_json,
            report_md_out=args.report_md,
            review_mode=args.review_mode,
            review_targets=args.review_target,
            review_local_model=args.review_local_model,
        )

    if args.command == "fix":
        return run_fix(
            args.file,
            args.out,
            report_json_out=args.report_json,
            report_md_out=args.report_md,
            review_mode=args.review_mode,
            review_targets=args.review_target,
            review_local_model=args.review_local_model,
        )

    if args.command == "batch-fix":
        return run_batch_fix(
            args.dir,
            args.out_dir,
            recursive=not args.no_recursive,
            review_mode=args.review_mode,
            review_targets=args.review_target,
            review_local_model=args.review_local_model,
        )

    if args.command == "review":
        return run_cli_review(
            args.input,
            args.findings,
            args.output,
            args.report,
        )

    parser.print_help()
    return 2


def run_cli_review(input_path: Path, findings_path: Path, output_path: Path, report_path: Path) -> int:
    import json

    try:
        import docx
    except ImportError:
        print("Error: python-docx is required for the review command", file=sys.stderr)
        return 1

    from thesis_format_fixer.review.adapter import WordReviewAdapter
    from thesis_format_fixer.review.contracts import StructuredReviewFinding, to_adapter_finding

    if not input_path.exists():
        print(f"Error: Input file missing: {input_path}", file=sys.stderr)
        return 1
    if not findings_path.exists():
        print(f"Error: Findings file missing: {findings_path}", file=sys.stderr)
        return 1

    try:
        findings_data = json.loads(findings_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Error: Invalid findings JSON: {e}", file=sys.stderr)
        return 1

    structured_findings = []
    if not isinstance(findings_data, list):
        print("Error: Findings JSON must be a list of findings", file=sys.stderr)
        return 1

    for item in findings_data:
        try:
            structured_findings.append(StructuredReviewFinding(**item))
        except Exception as e:
            print(f"Error: Invalid finding format in JSON: {e}", file=sys.stderr)
            return 1

    adapter_findings = []
    mapping_report = []

    for finding in structured_findings:
        map_result = to_adapter_finding(finding)
        mapping_report.append({
            "rule_id": finding.rule_id,
            "status": map_result.status,
            "reason": map_result.reason,
        })
        if map_result.status == "mapped" and map_result.adapter_finding:
            adapter_findings.append(map_result.adapter_finding)

    try:
        loaded_doc = docx.Document(input_path)
    except Exception as e:
        print(f"Error: Failed to load docx: {e}", file=sys.stderr)
        return 1

    adapter = WordReviewAdapter()
    apply_result = adapter.apply_findings(loaded_doc, adapter_findings)

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        loaded_doc.save(output_path)
    except Exception as e:
        print(f"Error: Failed to save output docx: {e}", file=sys.stderr)
        return 1

    final_report = {
        "schema_version": "review-report-v1",
        "input_file": str(input_path),
        "output_file": str(output_path),
        "mapping_details": mapping_report,
        "apply_summary": {
            "total": apply_result.total,
            "added": apply_result.added,
            "skipped": apply_result.skipped,
            "duplicate": apply_result.duplicate,
            "unsupported": apply_result.unsupported,
        },
        "apply_details": apply_result.details,
    }

    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(final_report, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        print(f"Error: Failed to write report: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
