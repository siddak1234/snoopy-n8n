import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from google.cloud import storage
from pydantic import BaseModel, ConfigDict, field_validator

X_INTERNAL_TOKEN = os.environ.get("RENDER_AUTH_TOKEN")
if not X_INTERNAL_TOKEN:
    raise RuntimeError("RENDER_AUTH_TOKEN environment variable must be set")
RENDER_DPI = int(os.getenv("RENDER_DPI", "300"))

app = FastAPI()


class RenderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    bucket: str
    object: str
    cleanup_prefix: bool = False

    @field_validator("job_id", "bucket", "object")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("must be a non-empty string")
        return value.strip()


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"detail": jsonable_encoder(exc.errors())})


def _validate_token(token: str | None) -> None:
    if token != X_INTERNAL_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _extract_page_number(file_path: Path) -> int:
    match = re.search(r"-(\d+)\.jpg$", file_path.name)
    if not match:
        raise ValueError(f"Unexpected render output filename: {file_path.name}")
    return int(match.group(1))


def _render_pdf(pdf_path: Path, output_prefix: Path) -> List[Path]:
    cmd = [
        "pdftoppm",
        "-jpeg",
        "-r",
        str(RENDER_DPI),
        str(pdf_path),
        str(output_prefix),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    rendered = sorted(output_prefix.parent.glob(f"{output_prefix.name}-*.jpg"))
    if not rendered:
        raise RuntimeError("No pages were rendered from the PDF")
    return rendered


def _delete_prefix(client: storage.Client, bucket_name: str, prefix: str) -> None:
    bucket = client.bucket(bucket_name)
    for blob in client.list_blobs(bucket, prefix=prefix):
        blob.delete()


@app.post("/render")
def render(request: RenderRequest, x_internal_token: str | None = Header(default=None, alias="X-Internal-Token")):
    _validate_token(x_internal_token)

    client = storage.Client()
    bucket = client.bucket(request.bucket)
    pages_prefix = f"pages/{request.job_id}/"

    temp_dir = Path(tempfile.mkdtemp(prefix="pdf-renderer-", dir="/tmp"))
    try:
        pdf_path = temp_dir / "input.pdf"
        bucket.blob(request.object).download_to_filename(str(pdf_path))

        if request.cleanup_prefix:
            _delete_prefix(client, request.bucket, pages_prefix)

        output_prefix = temp_dir / "page"
        rendered_pages = _render_pdf(pdf_path, output_prefix)

        for rendered in rendered_pages:
            page_number = _extract_page_number(rendered)
            destination = f"{pages_prefix}page-{page_number:03d}.jpg"
            bucket.blob(destination).upload_from_filename(str(rendered), content_type="image/jpeg")

        return {
            "job_id": request.job_id,
            "bucket": request.bucket,
            "object": request.object,
            "page_count": len(rendered_pages),
            "pages_prefix": pages_prefix,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except subprocess.CalledProcessError as exc:
        raise HTTPException(status_code=500, detail=f"Render command failed: {exc.stderr}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Render failed: {str(exc)}") from exc
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
