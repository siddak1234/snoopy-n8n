import json
import logging
import os
import re
from typing import Any

import requests
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("receipt_assembler")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="receipt-assembler", version="2.0.0")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TIMEOUT = 60
MAX_START_SCAN_PAGE = 30


class AssembleRequest(BaseModel):
    job_id: str = Field(min_length=1)
    bucket: str = Field(min_length=1)
    page_count: int = Field(ge=1)
    pages_prefix: str = Field(min_length=1)


class InvoiceGroup(BaseModel):
    group_id: str
    pages: list[int]
    kind: str
    multi_invoices_on_page: bool
    notes: str


class AssembleResponse(BaseModel):
    job_id: str
    bucket: str
    start_page: int
    groups: list[InvoiceGroup]
    stats: dict[str, int]


def _require_token(x_internal_token: str | None = Header(default=None)) -> None:
    expected = os.getenv("INTERNAL_TOKEN")
    if not expected:
        raise HTTPException(status_code=500, detail="INTERNAL_TOKEN is required")
    if x_internal_token != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _normalize_prefix(prefix: str) -> str:
    clean = prefix.strip()
    if not clean.endswith("/"):
        raise HTTPException(status_code=400, detail="pages_prefix must end with '/'")
    return clean


def _gcs_uri(bucket: str, prefix: str, page_num: int, ext: str) -> str:
    return f"gs://{bucket}/{prefix}page-{page_num:04d}.{ext}"


def _extract_json(text: str) -> dict[str, Any]:
    candidate = text.strip()
    match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if match:
        candidate = match.group(0)
    return json.loads(candidate)


def _is_not_found_error(body: str) -> bool:
    body_l = body.lower()
    markers = [
        "not found",
        "404",
        "file_uri",
        "could not fetch",
        "invalid",
        "does not exist",
        "permission denied",
    ]
    return any(m in body_l for m in markers)


def _gemini_pair_call(
    model: str,
    api_key: str,
    uri1: str,
    uri2: str,
    prompt: str,
    stats: dict[str, int],
) -> dict[str, Any]:
    url = f"{GEMINI_API_BASE}/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {"file_data": {"mime_type": "image/jpeg", "file_uri": uri1}},
                    {"file_data": {"mime_type": "image/jpeg", "file_uri": uri2}},
                    {"text": prompt},
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "maxOutputTokens": 128,
        },
    }

    stats["gemini_calls"] += 1
    resp = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT)
    if resp.status_code >= 400:
        raise RuntimeError(resp.text[:500])

    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("Malformed Gemini response")

    return _extract_json(text)


def _pair_with_fallback(
    bucket: str,
    prefix: str,
    page1: int,
    page2: int,
    prompt: str,
    model: str,
    api_key: str,
    stats: dict[str, int],
) -> dict[str, Any]:
    attempts: list[tuple[str, str]] = [
        ("jpg", "jpg"),
        ("jpeg", "jpg"),
        ("jpg", "jpeg"),
        ("jpeg", "jpeg"),
    ]

    last_error = ""
    for idx, (ext1, ext2) in enumerate(attempts):
        uri1 = _gcs_uri(bucket, prefix, page1, ext1)
        uri2 = _gcs_uri(bucket, prefix, page2, ext2)
        if idx > 0:
            stats["jpg_jpeg_fallbacks"] += 1
        try:
            return _gemini_pair_call(
                model=model,
                api_key=api_key,
                uri1=uri1,
                uri2=uri2,
                prompt=prompt,
                stats=stats,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            if not _is_not_found_error(last_error):
                break

    raise RuntimeError(last_error or "Gemini pair call failed")


def _detect_start_page(
    req: AssembleRequest,
    model: str,
    api_key: str,
    stats: dict[str, int],
    warnings: list[str],
) -> int:
    prompt = (
        "You are classifying two document pages from one packet. "
        "Identify whether they are Gideon summary or vendor invoice pages. "
        "Return STRICT JSON only with keys: "
        "first_vendor_page_in_pair (number or null), pair_label (summary|transition|invoice), "
        "confidence (0..1), reason (short)."
    )

    scan_to = min(req.page_count, MAX_START_SCAN_PAGE)
    logger.info("Start-page scan job_id=%s pages=1..%s", req.job_id, scan_to)

    for page in range(1, scan_to + 1):
        other = page + 1 if page < req.page_count else page
        stats["pair_checks"] += 1
        try:
            out = _pair_with_fallback(
                bucket=req.bucket,
                prefix=req.pages_prefix,
                page1=page,
                page2=other,
                prompt=prompt,
                model=model,
                api_key=api_key,
                stats=stats,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"start_scan_pair_{page}_{other}_failed")
            logger.warning("Start scan failed for pair %s,%s: %s", page, other, exc)
            continue

        first_vendor = out.get("first_vendor_page_in_pair")
        if isinstance(first_vendor, int) and first_vendor >= 1:
            logger.info("Detected start_page=%s from pair %s,%s", first_vendor, page, other)
            return min(first_vendor, req.page_count)

    warnings.append("start_page_not_found_by_page_30_defaulted_to_1")
    return 1


def _group_invoices(
    req: AssembleRequest,
    start_page: int,
    model: str,
    api_key: str,
    stats: dict[str, int],
    warnings: list[str],
) -> list[InvoiceGroup]:
    if start_page > req.page_count:
        return []

    groups: list[dict[str, Any]] = []
    current_pages = [start_page]
    current_note = ""

    prompt = (
        "Compare these two pages and decide if page 2 is a continuation of the SAME vendor invoice as page 1. "
        "Return STRICT JSON only with keys: same_invoice (boolean), continuation_signals (array of short strings), "
        "confidence (0..1), notes (short)."
    )

    p = start_page
    while p < req.page_count:
        p_next = p + 1
        stats["pair_checks"] += 1
        try:
            out = _pair_with_fallback(
                bucket=req.bucket,
                prefix=req.pages_prefix,
                page1=p,
                page2=p_next,
                prompt=prompt,
                model=model,
                api_key=api_key,
                stats=stats,
            )
            same_invoice = bool(out.get("same_invoice", False))
            notes = str(out.get("notes", "") or "")
        except Exception as exc:  # noqa: BLE001
            same_invoice = False
            notes = "pair_check_failed"
            warnings.append(f"group_pair_{p}_{p_next}_failed")
            logger.warning("Grouping check failed for pair %s,%s: %s", p, p_next, exc)

        if same_invoice:
            current_pages.append(p_next)
            if notes and not current_note:
                current_note = notes
        else:
            groups.append({"pages": current_pages, "notes": current_note or notes})
            current_pages = [p_next]
            current_note = ""

        p = p_next

    groups.append({"pages": current_pages, "notes": current_note})

    output: list[InvoiceGroup] = []
    for idx, g in enumerate(groups, start=1):
        note = g["notes"]
        if idx == 1 and warnings:
            prefix = ";".join(warnings)
            note = f"{prefix};{note}" if note else prefix

        output.append(
            InvoiceGroup(
                group_id=f"g{idx:04d}",
                pages=g["pages"],
                kind="invoice",
                multi_invoices_on_page=False,
                notes=note,
            )
        )

    logger.info("Grouped %s invoice chunks for job_id=%s", len(output), req.job_id)
    return output


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/assemble_invoices", response_model=AssembleResponse)
def assemble_invoices(
    req: AssembleRequest,
    x_internal_token: str | None = Header(default=None),
) -> AssembleResponse:
    _require_token(x_internal_token)

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is required")

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    req.pages_prefix = _normalize_prefix(req.pages_prefix)

    stats = {
        "gemini_calls": 0,
        "pair_checks": 0,
        "jpg_jpeg_fallbacks": 0,
    }
    warnings: list[str] = []

    start_page = _detect_start_page(
        req=req,
        model=model,
        api_key=api_key,
        stats=stats,
        warnings=warnings,
    )

    groups = _group_invoices(
        req=req,
        start_page=start_page,
        model=model,
        api_key=api_key,
        stats=stats,
        warnings=warnings,
    )

    if not groups and warnings:
        groups = [
            InvoiceGroup(
                group_id="g0001",
                pages=[start_page],
                kind="invoice",
                multi_invoices_on_page=False,
                notes=";".join(warnings),
            )
        ]

    return AssembleResponse(
        job_id=req.job_id,
        bucket=req.bucket,
        start_page=start_page,
        groups=groups,
        stats=stats,
    )
