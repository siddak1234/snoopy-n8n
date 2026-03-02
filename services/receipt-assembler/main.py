import logging
import os
import re
from typing import Any

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("receipt_assembler")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="receipt-assembler", version="1.0.0")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
PROMPT = "Classify this page as SUMMARY or RECEIPT or OTHER. Return ONLY one token: SUMMARY|RECEIPT|OTHER."


class AssembleRequest(BaseModel):
    job_id: str = Field(min_length=1)
    bucket: str = Field(min_length=1)
    start_page: int = Field(default=1, ge=1)
    page_count: int = Field(ge=1)
    pages_prefix: str | None = None


class ReceiptGroup(BaseModel):
    receipt_id: str
    pages: list[int]
    multi_receipts_on_page: bool
    notes: str


class AssembleResponse(BaseModel):
    job_id: str
    receipt_start_page: int
    receipts: list[ReceiptGroup]
    stats: dict[str, int]


def _normalize_prefix(job_id: str, pages_prefix: str | None) -> str:
    if pages_prefix:
        return pages_prefix.strip("/") + "/"
    return f"pages/{job_id}/"


def _extract_label(text: str) -> str:
    token = (text or "").strip().upper()
    token = re.sub(r"[^A-Z|]", "", token)
    for option in ("SUMMARY", "RECEIPT", "OTHER"):
        if option in token:
            return option
    return "OTHER"


def _call_gemini(model: str, api_key: str, gcs_uri: str) -> str:
    url = f"{GEMINI_API_BASE}/{model}:generateContent?key={api_key}"
    payload: dict[str, Any] = {
        "contents": [
            {
                "parts": [
                    {"text": PROMPT},
                    {
                        "file_data": {
                            "mime_type": "image/jpeg",
                            "file_uri": gcs_uri,
                        }
                    },
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 16,
        },
    }

    resp = requests.post(url, json=payload, timeout=(10, 60))
    if resp.status_code >= 400:
        raise RuntimeError(f"Gemini error ({resp.status_code}): {resp.text[:200]}")

    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        text = "OTHER"
    return _extract_label(text)


def _classify_page(
    page_number: int,
    bucket: str,
    pages_prefix: str,
    model: str,
    api_key: str,
) -> tuple[str, int]:
    calls = 0
    candidates = [
        f"gs://{bucket}/{pages_prefix}page-{page_number:04d}.jpg",
        f"gs://{bucket}/{pages_prefix}page-{page_number:04d}.jpeg",
    ]

    for uri in candidates:
        calls += 1
        try:
            label = _call_gemini(model=model, api_key=api_key, gcs_uri=uri)
            return label, calls
        except Exception as exc:  # noqa: BLE001
            logger.warning("Page %s classify failed for %s: %s", page_number, uri, exc)

    return "OTHER", calls


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/assemble_receipts", response_model=AssembleResponse)
def assemble_receipts(req: AssembleRequest) -> AssembleResponse:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is required")

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    pages_prefix = _normalize_prefix(req.job_id, req.pages_prefix)

    gemini_calls = 0
    receipt_pages: list[int] = []

    for page_num in range(req.start_page, req.page_count + 1):
        label, calls = _classify_page(
            page_number=page_num,
            bucket=req.bucket,
            pages_prefix=pages_prefix,
            model=model,
            api_key=api_key,
        )
        gemini_calls += calls
        if label == "RECEIPT":
            receipt_pages.append(page_num)

    groups: list[list[int]] = []
    for page in receipt_pages:
        if not groups or page != groups[-1][-1] + 1:
            groups.append([page])
        else:
            groups[-1].append(page)

    receipts: list[ReceiptGroup] = []
    for idx, pages in enumerate(groups, start=1):
        receipts.append(
            ReceiptGroup(
                receipt_id=f"r{idx:04d}",
                pages=pages,
                multi_receipts_on_page=False,
                notes="POC grouping of consecutive receipt pages",
            )
        )

    receipt_start_page = receipt_pages[0] if receipt_pages else 0

    return AssembleResponse(
        job_id=req.job_id,
        receipt_start_page=receipt_start_page,
        receipts=receipts,
        stats={"gemini_calls": gemini_calls},
    )
