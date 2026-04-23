"""FastAPI app for minimal Appsmith integration."""

from __future__ import annotations

import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from .service import ApiJobError, ApiJobService


def create_app(service: ApiJobService | None = None) -> FastAPI:
    app = FastAPI(title="Thesis Format Fixer API", version="0.1.0")
    job_service = service or ApiJobService()

    def get_service() -> ApiJobService:
        return job_service

    def _error_payload(*, job_id: str | None, mode: str, message: str, status: str = "failed") -> dict[str, object]:
        return {
            "job_id": job_id,
            "status": status,
            "mode": mode,
            "input_filename": None,
            "output_filename": None,
            "summary": {},
            "user_summary": {
                "overall_status": "",
                "processing_label": "",
                "categorized": {
                    "auto_processed": [],
                    "detected_not_auto_fixed": [],
                    "manual_review_required": [],
                },
                "counts": {
                    "auto_processed": 0,
                    "detected_not_auto_fixed": 0,
                    "manual_review_required": 0,
                },
                "key_issues": [],
                "next_steps": [],
                "artifacts": [],
            },
            "artifacts": {
                "input_file": None,
                "report_json": None,
                "report_md": None,
                "user_summary_md": None,
                "fixed_docx": None,
                "download_fixed_docx_url": None,
                "download_report_md_url": None,
            },
            "error": message,
        }

    @app.exception_handler(ApiJobError)
    async def api_job_error_handler(_: object, exc: ApiJobError) -> JSONResponse:
        return JSONResponse(status_code=400, content=_error_payload(job_id=None, mode="unknown", message=str(exc)))

    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(_: object, exc: FileNotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content=_error_payload(job_id=None, mode="unknown", message=str(exc)))

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/jobs/check")
    async def create_check_job(
        file: UploadFile = File(...),
        service_obj: ApiJobService = Depends(get_service),
    ) -> object:
        try:
            content = await file.read()
            return service_obj.create_job(mode="check", filename=file.filename, content=content)
        except ApiJobError as exc:
            return JSONResponse(status_code=400, content=_error_payload(job_id=None, mode="check", message=str(exc)))

    @app.post("/api/jobs/fix")
    async def create_fix_job(
        file: UploadFile = File(...),
        service_obj: ApiJobService = Depends(get_service),
    ) -> object:
        try:
            content = await file.read()
            return service_obj.create_job(mode="fix", filename=file.filename, content=content)
        except ApiJobError as exc:
            return JSONResponse(status_code=400, content=_error_payload(job_id=None, mode="fix", message=str(exc)))

    @app.get("/api/jobs/{job_id}")
    async def get_job(job_id: str, service_obj: ApiJobService = Depends(get_service)) -> dict[str, object]:
        return service_obj.get_job(job_id)

    @app.get("/api/jobs/{job_id}/download/fixed-docx")
    async def download_fixed_docx(job_id: str, service_obj: ApiJobService = Depends(get_service)) -> FileResponse:
        target = service_obj.get_download_path(job_id, artifact="fixed-docx")
        return FileResponse(
            path=target,
            filename=target.name,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    @app.get("/api/jobs/{job_id}/download/report-md")
    async def download_report_md(job_id: str, service_obj: ApiJobService = Depends(get_service)) -> FileResponse:
        target = service_obj.get_download_path(job_id, artifact="report-md")
        return FileResponse(path=target, filename=target.name, media_type="text/markdown; charset=utf-8")

    @app.exception_handler(HTTPException)
    async def http_exception_handler(_: object, exc: HTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "request failed"
        return JSONResponse(status_code=exc.status_code, content=_error_payload(job_id=None, mode="unknown", message=detail))

    return app


app = create_app()


def main() -> None:
    uvicorn.run("thesis_format_fixer.api.app:app", host="127.0.0.1", port=8000, reload=False)
