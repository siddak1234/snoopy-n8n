import json
import logging
import os
import re
from dataclasses import dataclass
from typing import Any

import requests
from fastapi import FastAPI, Header, HTTPException
from google.cloud import storage
from pydantic import BaseModel, Field

logger = logging.getLogger("receipt_assembler")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="receipt-assembler", version="3.0.0")

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
REQUEST_TIMEOUT = 60
MAX_START_SCAN_PAGE = 30
MAX_DEBUG_TRACES = 200


class AssembleInvoicesRequest(BaseModel):
    job_id: str = Field(min_length=1)
    bucket: str = Field(min_length=1)
    page_count: int = Field(ge=1)
    pages_prefix: str = Field(min_length=1)
    debug: bool = False


class AssembleFromManifestRequest(BaseModel):
    bucket: str = Field(min_length=1)
    manifest_object: str = Field(min_length=1)
    max_pages: int | None = Field(default=None, ge=1)
    debug: bool = False


class InvoiceGroup(BaseModel):
    group_id: str
    pages: list[int]
    kind: str
    multi_invoices_on_page: bool
    notes: str


class BaseAssembleResponse(BaseModel):
    job_id: str
    bucket: str
    start_page: int
    groups: list[InvoiceGroup]
    stats: dict[str, int]


class AssembleFromManifestResponse(BaseAssembleResponse):
    debug_traces: list[dict[str, Any]]


@dataclass
class RunContext:
    job_id: str
    bucket: str
    page_count: int
    pages_prefix: str
    debug: bool


def _require_token(x_internal_token: str | None) -> None:
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


def _derive_job_id_from_manifest_object(manifest_object: str) -> str:
    if not manifest_object.startswith("manifests/"):
        raise HTTPException(status_code=400, detail="manifest_object must start with 'manifests/'")
    if not manifest_object.endswith(".json"):
        raise HTTPException(status_code=400, detail="manifest_object must end with '.json'")

    job_id = manifest_object[len("manifests/") : -len(".json")]
    if not job_id:
        raise HTTPException(status_code=400, detail="Could not derive job_id from manifest_object")
    return job_id


def _extract_json(text: str) -> dict[str, Any]:
    candidate = text.strip()
    match = re.search(r"\{.*\}", candidate, re.DOTALL)
    if match:
        candidate = match.group(0)
    return json.loads(candidate)


def _parse_page_count_from_manifest(content: str) -> int | None:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict):
        value = parsed.get("page_count")
        if isinstance(value, int) and value > 0:
            return value
        if isinstance(value, str) and value.isdigit() and int(value) > 0:
            return int(value)

    return None


def _storage_client() -> storage.Client:
    return storage.Client()


def _gcs_uri(bucket: str, prefix: str, page_num: int, ext: str) -> str:
    return f"gs://{bucket}/{prefix}page-{page_num:04d}.{ext}"


def _resolve_existing_page_uri(
    client: storage.Client,
    bucket_name: str,
    prefix: str,
    page_num: int,
    stats: dict[str, int],
) -> str:
    bucket = client.bucket(bucket_name)
    jpg_name = f"{prefix}page-{page_num:04d}.jpg"
    jpeg_name = f"{prefix}page-{page_num:04d}.jpeg"

    if bucket.blob(jpg_name).exists(client=client):
        return _gcs_uri(bucket_name, prefix, page_num, "jpg")

    if bucket.blob(jpeg_name).exists(client=client):
        stats["jpg_jpeg_fallbacks"] += 1
        return _gcs_uri(bucket_name, prefix, page_num, "jpeg")

    raise HTTPException(
        status_code=400,
        detail=(
            "Missing rendered page object. "
            f"Expected under prefix '{prefix}'. "
            f"Tried '{jpg_name}' and '{jpeg_name}'."
        ),
    )


def _record_trace(
    debug_enabled: bool,
    traces: list[dict[str, Any]],
    entry: dict[str, Any],
) -> None:
    if debug_enabled and len(traces) < MAX_DEBUG_TRACES:
        traces.append(entry)


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
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("Malformed Gemini response") from exc

    return _extract_json(text)


def _detect_start_page(
    ctx: RunContext,
    client: storage.Client,
    model: str,
    api_key: str,
    stats: dict[str, int],
    warnings: list[str],
    traces: list[dict[str, Any]],
) -> int:
    prompt = (
        "You are classifying two document pages from one packet. "
        "Identify whether they are Gideon summary or vendor invoice pages. "
        "Return STRICT JSON only with keys: "
        "first_vendor_page_in_pair (number or null), pair_label (summary|transition|invoice), "
        "confidence (0..1), reason (short)."
    )

    scan_to = min(ctx.page_count, MAX_START_SCAN_PAGE)
    logger.info("Start-page scan job_id=%s pages=1..%s", ctx.job_id, scan_to)

    for page in range(1, scan_to + 1):
        other = page + 1 if page < ctx.page_count else page
        stats["pair_checks"] += 1

        uri1 = _resolve_existing_page_uri(client, ctx.bucket, ctx.pages_prefix, page, stats)
        uri2 = _resolve_existing_page_uri(client, ctx.bucket, ctx.pages_prefix, other, stats)

        try:
            out = _gemini_pair_call(
                model=model,
                api_key=api_key,
                uri1=uri1,
                uri2=uri2,
                prompt=prompt,
                stats=stats,
            )
            _record_trace(
                ctx.debug,
                traces,
                {"phase": "start_scan", "pair": [page, other], "uris": [uri1, uri2], "result": out, "error": ""},
            )
        except Exception as exc:  # noqa: BLE001
            err = str(exc)
            warnings.append(f"start_scan_pair_{page}_{other}_failed")
            logger.warning("Start scan failed for pair %s,%s: %s", page, other, err)
            _record_trace(
                ctx.debug,
                traces,
                {"phase": "start_scan", "pair": [page, other], "uris": [uri1, uri2], "result": {}, "error": err[:300]},
            )
            continue

        first_vendor = out.get("first_vendor_page_in_pair")
        if isinstance(first_vendor, int) and first_vendor >= 1:
            logger.info("Detected start_page=%s from pair %s,%s", first_vendor, page, other)
            return min(first_vendor, ctx.page_count)

    warnings.append("start_page_not_found_by_page_30_defaulted_to_1")
    return 1


def _group_invoices(
    ctx: RunContext,
    start_page: int,
    client: storage.Client,
    model: str,
    api_key: str,
    stats: dict[str, int],
    warnings: list[str],
    traces: list[dict[str, Any]],
) -> list[InvoiceGroup]:
    if start_page > ctx.page_count:
        return []

    prompt = (
        "Compare these two pages and decide if page 2 is a continuation of the SAME vendor invoice as page 1. "
        "Return STRICT JSON only with keys: same_invoice (boolean), continuation_signals (array of short strings), "
        "confidence (0..1), notes (short)."
    )

    groups_raw: list[dict[str, Any]] = []
    current_pages = [start_page]
    current_note = ""

    p = start_page
    while p < ctx.page_count:
        p_next = p + 1
        stats["pair_checks"] += 1

        uri1 = _resolve_existing_page_uri(client, ctx.bucket, ctx.pages_prefix, p, stats)
        uri2 = _resolve_existing_page_uri(client, ctx.bucket, ctx.pages_prefix, p_next, stats)

        try:
            out = _gemini_pair_call(
                model=model,
                api_key=api_key,
                uri1=uri1,
                uri2=uri2,
                prompt=prompt,
                stats=stats,
            )
            same_invoice = bool(out.get("same_invoice", False))
            notes = str(out.get("notes", "") or "")
            _record_trace(
                ctx.debug,
                traces,
                {"phase": "group", "pair": [p, p_next], "uris": [uri1, uri2], "result": out, "error": ""},
            )
        except Exception as exc:  # noqa: BLE001
            err = str(exc)
            same_invoice = False
            notes = "pair_check_failed"
            warnings.append(f"group_pair_{p}_{p_next}_failed")
            logger.warning("Grouping failed for pair %s,%s: %s", p, p_next, err)
            _record_trace(
                ctx.debug,
                traces,
                {"phase": "group", "pair": [p, p_next], "uris": [uri1, uri2], "result": {}, "error": err[:300]},
            )

        if same_invoice:
            current_pages.append(p_next)
            if notes and not current_note:
                current_note = notes
        else:
            groups_raw.append({"pages": current_pages, "notes": current_note or notes})
            current_pages = [p_next]
            current_note = ""

        p = p_next

    groups_raw.append({"pages": current_pages, "notes": current_note})

    output: list[InvoiceGroup] = []
    for idx, raw in enumerate(groups_raw, start=1):
        note = raw["notes"]
        if idx == 1 and warnings:
            prefix = ";".join(warnings)
            note = f"{prefix};{note}" if note else prefix

        output.append(
            InvoiceGroup(
                group_id=f"g{idx:04d}",
                pages=raw["pages"],
                kind="invoice",
                multi_invoices_on_page=False,
                notes=note,
            )
        )

    logger.info("Grouped %s invoice chunks for job_id=%s", len(output), ctx.job_id)
    return output


def _run_assembly(ctx: RunContext) -> tuple[int, list[InvoiceGroup], dict[str, int], list[dict[str, Any]]]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is required")

    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    client = _storage_client()

    stats = {
        "gemini_calls": 0,
        "pair_checks": 0,
        "jpg_jpeg_fallbacks": 0,
    }
    warnings: list[str] = []
    traces: list[dict[str, Any]] = []

    start_page = _detect_start_page(
        ctx=ctx,
        client=client,
        model=model,
        api_key=api_key,
        stats=stats,
        warnings=warnings,
        traces=traces,
    )

    groups = _group_invoices(
        ctx=ctx,
        start_page=start_page,
        client=client,
        model=model,
        api_key=api_key,
        stats=stats,
        warnings=warnings,
        traces=traces,
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

    return start_page, groups, stats, traces


def _fetch_manifest_text(bucket: str, manifest_object: str) -> str:
    client = _storage_client()
    blob = client.bucket(bucket).blob(manifest_object)
    if not blob.exists(client=client):
        raise HTTPException(status_code=404, detail="Manifest object not found in GCS")
    return blob.download_as_text()


@app.get("/healthz")
def healthz() -> dict[str, bool]:
    return {"ok": True}


@app.post("/assemble_invoices", response_model=BaseAssembleResponse)
def assemble_invoices(
    req: AssembleInvoicesRequest,
    x_internal_token: str | None = Header(default=None),
) -> BaseAssembleResponse:
    _require_token(x_internal_token)

    ctx = RunContext(
        job_id=req.job_id,
        bucket=req.bucket,
        page_count=req.page_count,
        pages_prefix=_normalize_prefix(req.pages_prefix),
        debug=req.debug,
    )

    start_page, groups, stats, _ = _run_assembly(ctx)
    return BaseAssembleResponse(
        job_id=ctx.job_id,
        bucket=ctx.bucket,
        start_page=start_page,
        groups=groups,
        stats=stats,
    )


@app.post("/assemble_from_manifest", response_model=AssembleFromManifestResponse)
def assemble_from_manifest(
    req: AssembleFromManifestRequest,
    x_internal_token: str | None = Header(default=None),
) -> AssembleFromManifestResponse:
    _require_token(x_internal_token)

    job_id = _derive_job_id_from_manifest_object(req.manifest_object)
    pages_prefix = f"pages/{job_id}/"

    manifest_text = _fetch_manifest_text(req.bucket, req.manifest_object)
    manifest_page_count = _parse_page_count_from_manifest(manifest_text)

    if manifest_page_count is None and req.max_pages is None:
        raise HTTPException(
            status_code=400,
            detail="Manifest missing page_count and max_pages not provided",
        )

    page_count = manifest_page_count if manifest_page_count is not None else req.max_pages
    if req.max_pages is not None:
        page_count = min(page_count, req.max_pages)

    ctx = RunContext(
        job_id=job_id,
        bucket=req.bucket,
        page_count=page_count,
        pages_prefix=pages_prefix,
        debug=req.debug,
    )

    start_page, groups, stats, traces = _run_assembly(ctx)

    return AssembleFromManifestResponse(
        job_id=ctx.job_id,
        bucket=ctx.bucket,
        start_page=start_page,
        groups=groups,
        stats=stats,
        debug_traces=traces,
    )
