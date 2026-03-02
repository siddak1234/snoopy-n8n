#!/usr/bin/env python3
"""Minimal smoke helper for Vertex Gemini gs:// multimodal request payload.

By default it performs a dry-run and prints endpoint/payload.
Pass --run to execute request using ADC.
"""

import argparse
import json
import os

import google.auth
import requests
from google.auth.transport.requests import Request as GoogleAuthRequest

SCOPE = "https://www.googleapis.com/auth/cloud-platform"


def endpoint(project: str, location: str, model: str) -> str:
    return (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}/"
        f"locations/{location}/publishers/google/models/{model}:generateContent"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--uri1", required=True)
    parser.add_argument("--uri2", required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    project = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    if not project:
        raise SystemExit("GOOGLE_CLOUD_PROJECT is required")

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": "Return ONLY JSON: {\"same_invoice\":true|false}"},
                    {"fileData": {"mimeType": "image/jpeg", "fileUri": args.uri1}},
                    {"fileData": {"mimeType": "image/jpeg", "fileUri": args.uri2}},
                ],
            }
        ],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 32},
    }

    ep = endpoint(project, location, model)
    print("endpoint:", ep)
    print("payload:", json.dumps(payload, separators=(",", ":")))

    if not args.run:
        print("dry-run complete (use --run to execute)")
        return

    creds, _ = google.auth.default(scopes=[SCOPE])
    creds.refresh(GoogleAuthRequest())

    resp = requests.post(
        ep,
        headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
        json=payload,
        timeout=60,
    )
    print("status:", resp.status_code)
    print(resp.text[:1200])


if __name__ == "__main__":
    main()
