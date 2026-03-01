import json
import logging
import os
import tempfile
from pathlib import Path
from typing import List

import fitz  # PyMuPDF
from fastapi import Depends, FastAPI, Header, HTTPException
from google.api_core.exceptions import NotFound
from google.cloud import storage
from pydantic import BaseModel, Field

logger = logging.getLogger("pdf_renderer")
logging.basicConfig(level=logging.INFO)

DOWNLOAD_TIMEOUT_SECONDS = 300
UPLOAD_TIMEOUT_SECONDS = 120
JPEG_DPI = 150
JPEG_QUALITY = 85

app = FastAPI(title="pdf-renderer", version="1.0.0")


class RenderRequest(BaseModel):
    job_id: str = Field(min_length=1)
    bucket: str = Field(min_length=1)
    object: str = Field(min_length=1)


class PageResult(BaseModel):
    page: int
    gcs_object: str


class RenderResponse(BaseModel):
    job_id: str
    bucket: str
    source_object: str
    pages_prefix: str
    page_count: int
    pages: List[PageResult]


def require_token(x_internal_token: str | None = Header(default=None)) -> None:
    expected = os.getenv("INTERNAL_TOKEN")
    if not expected:
        logger.error("INTERNAL_TOKEN is not configured")
        raise HTTPException(status_code=500, detail="Server auth configuration error")

    if x_internal_token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def render_and_upload_pages(req: RenderRequest) -> RenderResponse:
    client = storage.Client()
    bucket = client.bucket(req.bucket)
    source_blob = bucket.blob(req.object)

    tmp_pdf_path = None
    page_results: List[PageResult] = []

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir="/tmp") as tmp_pdf:
            tmp_pdf_path = tmp_pdf.name

        try:
            source_blob.download_to_filename(tmp_pdf_path, timeout=DOWNLOAD_TIMEOUT_SECONDS)
        except NotFound as exc:
            raise HTTPException(status_code=404, detail="Source PDF not found in GCS") from exc

        doc = fitz.open(tmp_pdf_path)
        try:
            page_count = doc.page_count
            if page_count == 0:
                raise HTTPException(status_code=400, detail="Source PDF has zero pages")

            pages_prefix = f"pages/{req.job_id}/"

            for page_number in range(page_count):
                page = doc.load_page(page_number)
                pix = page.get_pixmap(dpi=JPEG_DPI, alpha=False)

                page_name = f"page-{page_number + 1:04d}.jpg"
                gcs_object = f"{pages_prefix}{page_name}"

                tmp_page_path = None
                try:
                    with tempfile.NamedTemporaryFile(
                        suffix=".jpg", delete=False, dir="/tmp"
                    ) as tmp_page:
                        tmp_page_path = tmp_page.name

                    pix.save(tmp_page_path, output="jpeg", jpg_quality=JPEG_QUALITY)

                    page_blob = bucket.blob(gcs_object)
                    page_blob.upload_from_filename(
                        tmp_page_path,
                        content_type="image/jpeg",
                        timeout=UPLOAD_TIMEOUT_SECONDS,
                    )
                finally:
                    if tmp_page_path and Path(tmp_page_path).exists():
                        Path(tmp_page_path).unlink(missing_ok=True)

                page_results.append(PageResult(page=page_number + 1, gcs_object=gcs_object))
        finally:
            doc.close()

        manifest_object = f"results/{req.job_id}/pages_manifest.json"
        manifest_payload = {
            "job_id": req.job_id,
            "bucket": req.bucket,
            "source_object": req.object,
            "pages_prefix": f"pages/{req.job_id}/",
            "page_count": len(page_results),
            "pages": [p.model_dump() for p in page_results],
        }

        bucket.blob(manifest_object).upload_from_string(
            json.dumps(manifest_payload, separators=(",", ":")),
            content_type="application/json",
            timeout=UPLOAD_TIMEOUT_SECONDS,
        )

        return RenderResponse(
            job_id=req.job_id,
            bucket=req.bucket,
            source_object=req.object,
            pages_prefix=f"pages/{req.job_id}/",
            page_count=len(page_results),
            pages=page_results,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Render job failed for job_id=%s", req.job_id)
        raise HTTPException(status_code=500, detail="Render job failed") from exc
    finally:
        if tmp_pdf_path and Path(tmp_pdf_path).exists():
            Path(tmp_pdf_path).unlink(missing_ok=True)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/render", response_model=RenderResponse)
def render(req: RenderRequest, _: None = Depends(require_token)) -> RenderResponse:
    return render_and_upload_pages(req)
