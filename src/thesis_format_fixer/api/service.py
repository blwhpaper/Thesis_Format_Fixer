"""Filesystem-backed job service for the HTTP API."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from tempfile import gettempdir
from typing import Any
from uuid import uuid4

from thesis_format_fixer.app.runner import run_check_with_details, run_fix_with_details

from .models import build_job_result


class ApiJobError(Exception):
    """Raised when the API receives an invalid request."""


@dataclass(frozen=True, slots=True)
class JobFiles:
    root: Path
    input_dir: Path
    output_dir: Path
    metadata_path: Path
    input_file: Path
    report_json: Path
    report_md: Path
    user_summary_md: Path
    fixed_docx: Path


class ApiJobService:
    def __init__(self, jobs_root: Path | None = None) -> None:
        base_root = jobs_root or Path(
            os.environ.get("THESIS_FORMAT_FIXER_API_ROOT", Path(gettempdir()) / "thesis-format-fixer-api")
        )
        self._jobs_root = base_root
        self._jobs_root.mkdir(parents=True, exist_ok=True)

    def create_job(
        self,
        *,
        mode: str,
        filename: str | None,
        content: bytes,
    ) -> dict[str, Any]:
        normalized_mode = mode.strip().lower()
        if normalized_mode not in {"check", "fix"}:
            raise ApiJobError(f"unsupported mode: {mode}")
        safe_name = self._validate_upload(filename=filename, content=content)

        job_id = uuid4().hex
        files = self._prepare_job_files(job_id=job_id, filename=safe_name)
        files.input_file.write_bytes(content)

        payload: dict[str, Any] | None = None
        error: str | None = None
        status = "completed"
        output_filename = None

        try:
            if normalized_mode == "check":
                _, payload, _, _ = run_check_with_details(
                    files.input_file,
                    report_json_out=files.report_json,
                    report_md_out=files.report_md,
                )
            else:
                _, payload, _, _ = run_fix_with_details(
                    files.input_file,
                    files.fixed_docx,
                    report_json_out=files.report_json,
                    report_md_out=files.report_md,
                )
                output_filename = files.fixed_docx.name
        except Exception as exc:
            status = "failed"
            error = str(exc)

        if payload is not None:
            artifacts = payload.get("artifacts") or {}
            output_filename = output_filename or self._filename_or_none(artifacts.get("fixed_docx"))

        artifacts = payload.get("artifacts") if payload is not None else {}
        user_summary_path = self._path_from_payload(artifacts, "user_summary_md") or self._resolve_existing_path(
            files.user_summary_md
        )
        report_json_path = self._path_from_payload(artifacts, "report_json") or self._resolve_existing_path(
            files.report_json
        )
        report_md_path = self._path_from_payload(artifacts, "report_md") or self._resolve_existing_path(
            files.report_md
        )
        fixed_docx_path = self._path_from_payload(artifacts, "fixed_docx") or self._resolve_existing_path(
            files.fixed_docx
        )

        result = build_job_result(
            job_id=job_id,
            mode=normalized_mode,
            status=status,
            input_filename=safe_name,
            output_filename=output_filename,
            payload=payload,
            input_path=files.input_file,
            report_json_path=report_json_path,
            report_md_path=report_md_path,
            user_summary_path=user_summary_path,
            fixed_docx_path=fixed_docx_path,
            error=error,
        )
        metadata = result.to_dict()
        files.metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        return metadata

    def get_job(self, job_id: str) -> dict[str, Any]:
        files = self._existing_job_files(job_id)
        if not files.metadata_path.exists():
            raise FileNotFoundError(f"job not found: {job_id}")
        return json.loads(files.metadata_path.read_text(encoding="utf-8"))

    def get_download_path(self, job_id: str, *, artifact: str) -> Path:
        files = self._existing_job_files(job_id)
        mapping = {
            "fixed-docx": files.fixed_docx,
            "report-md": files.report_md,
        }
        target = mapping.get(artifact)
        if target is None or not target.exists():
            raise FileNotFoundError(f"artifact not found: {artifact}")
        return target

    def _prepare_job_files(self, *, job_id: str, filename: str) -> JobFiles:
        root = self._jobs_root / job_id
        input_dir = root / "input"
        output_dir = root / "output"
        input_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(filename).stem
        return JobFiles(
            root=root,
            input_dir=input_dir,
            output_dir=output_dir,
            metadata_path=root / "job.json",
            input_file=input_dir / filename,
            report_json=output_dir / f"{stem}.report.json",
            report_md=output_dir / f"{stem}.report.md",
            user_summary_md=output_dir / ("fix.user_summary.md" if stem else "fix.user_summary.md"),
            fixed_docx=output_dir / f"{stem}.fixed.docx",
        )

    def _existing_job_files(self, job_id: str) -> JobFiles:
        root = self._jobs_root / job_id
        if not root.exists():
            raise FileNotFoundError(f"job not found: {job_id}")
        metadata = root / "job.json"
        input_dir = root / "input"
        output_dir = root / "output"
        input_files = sorted(path for path in input_dir.iterdir() if path.is_file()) if input_dir.exists() else []
        input_file = input_files[0] if input_files else input_dir / "missing.docx"
        stem = input_file.stem
        return JobFiles(
            root=root,
            input_dir=input_dir,
            output_dir=output_dir,
            metadata_path=metadata,
            input_file=input_file,
            report_json=output_dir / f"{stem}.report.json",
            report_md=output_dir / f"{stem}.report.md",
            user_summary_md=output_dir / "fix.user_summary.md",
            fixed_docx=output_dir / f"{stem}.fixed.docx",
        )

    def _validate_upload(self, *, filename: str | None, content: bytes) -> str:
        candidate = Path(filename or "").name
        if not candidate:
            raise ApiJobError("input file is required")
        if Path(candidate).suffix.lower() != ".docx":
            raise ApiJobError("input file must be a .docx file")
        if not content:
            raise ApiJobError("input file is empty")
        return candidate

    @staticmethod
    def _resolve_existing_path(path: Path) -> Path | None:
        return path if path.exists() else None

    @staticmethod
    def _filename_or_none(raw_path: Any) -> str | None:
        if not raw_path or not isinstance(raw_path, str):
            return None
        return Path(raw_path).name

    @staticmethod
    def _path_from_payload(artifacts: Any, key: str) -> Path | None:
        if not isinstance(artifacts, dict):
            return None
        raw_path = artifacts.get(key)
        if not isinstance(raw_path, str) or not raw_path.strip():
            return None
        path = Path(raw_path)
        return path if path.exists() else None
