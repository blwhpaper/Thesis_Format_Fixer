"""Thin API response models for Appsmith integration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ApiJobArtifacts:
    input_file: str
    report_json: str | None
    report_md: str | None
    user_summary_md: str | None
    fixed_docx: str | None
    download_fixed_docx_url: str | None
    download_report_md_url: str | None


@dataclass(frozen=True, slots=True)
class ApiJobResult:
    job_id: str
    status: str
    mode: str
    input_filename: str
    output_filename: str | None
    summary: dict[str, Any]
    user_summary: dict[str, Any]
    artifacts: ApiJobArtifacts
    error: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "mode": self.mode,
            "input_filename": self.input_filename,
            "output_filename": self.output_filename,
            "summary": self.summary,
            "user_summary": self.user_summary,
            "artifacts": {
                "input_file": self.artifacts.input_file,
                "report_json": self.artifacts.report_json,
                "report_md": self.artifacts.report_md,
                "user_summary_md": self.artifacts.user_summary_md,
                "fixed_docx": self.artifacts.fixed_docx,
                "download_fixed_docx_url": self.artifacts.download_fixed_docx_url,
                "download_report_md_url": self.artifacts.download_report_md_url,
            },
            "error": self.error,
        }


def build_appsmith_user_summary(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("user_summary") or {}
    return {
        "overall_status": summary.get("overall_status", ""),
        "processing_label": summary.get("processing_label", ""),
        "categorized": {
            "auto_processed": list(summary.get("auto_fixed_items") or []),
            "detected_not_auto_fixed": list(summary.get("detected_but_not_fixed_items") or []),
            "manual_review_required": list(summary.get("manual_review_items") or []),
        },
        "counts": {
            "auto_processed": int(summary.get("auto_fixed_count", 0)),
            "detected_not_auto_fixed": int(summary.get("detected_not_auto_modified_count", 0)),
            "manual_review_required": int(summary.get("manual_review_required_count", 0)),
        },
        "key_issues": list(summary.get("key_issues") or []),
        "next_steps": list(summary.get("next_steps") or []),
        "artifacts": list(summary.get("artifacts") or []),
    }


def build_job_result(
    *,
    job_id: str,
    mode: str,
    status: str,
    input_filename: str,
    output_filename: str | None,
    payload: dict[str, Any] | None,
    input_path: Path,
    report_json_path: Path | None,
    report_md_path: Path | None,
    user_summary_path: Path | None,
    fixed_docx_path: Path | None,
    error: str | None,
) -> ApiJobResult:
    safe_payload = payload or {}
    return ApiJobResult(
        job_id=job_id,
        status=status,
        mode=mode,
        input_filename=input_filename,
        output_filename=output_filename,
        summary=dict(safe_payload.get("summary") or {}),
        user_summary=build_appsmith_user_summary(safe_payload),
        artifacts=ApiJobArtifacts(
            input_file=str(input_path),
            report_json=str(report_json_path) if report_json_path is not None else None,
            report_md=str(report_md_path) if report_md_path is not None else None,
            user_summary_md=str(user_summary_path) if user_summary_path is not None else None,
            fixed_docx=str(fixed_docx_path) if fixed_docx_path is not None else None,
            download_fixed_docx_url=(
                f"/api/jobs/{job_id}/download/fixed-docx" if fixed_docx_path is not None else None
            ),
            download_report_md_url=(
                f"/api/jobs/{job_id}/download/report-md" if report_md_path is not None else None
            ),
        ),
        error=error,
    )
