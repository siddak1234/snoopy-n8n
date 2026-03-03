# n8n-nodes-mistral-document-ai

Custom n8n community node for Mistral Document AI OCR using binary PDF/image input.

## Features

- Reuses built-in n8n credential type: **Mistral Cloud API** (`mistralCloudApi`)
- Uses the same credential dropdown as built-in Mistral nodes (no separate API key entry in this node)
- Node: **Mistral Document AI**
- Binary input OCR (`data` by default)
- Table extraction mode mapping:
  - `inline` -> `table_format: null`
  - `markdown` -> `table_format: "markdown"`
  - `html` -> `table_format: "html"`
- Header/footer, images, hyperlinks toggles
- Document Annotation options:
  - format (`json`/`markdown`)
  - prompt
  - JSON schema (for JSON output)
- Annotation granularity toggle:
  - `Annotate Per Page = false` (default): one combined OCR/annotation response for requested page range
  - `Annotate Per Page = true`: one OCR/annotation request per explicit page and one output item per page
- Direct OCR multipart attempt with fallback to:
  1. `POST /v1/files`
  2. `POST /v1/ocr` with `document.file_id`
- Output normalization with optional raw response passthrough

## Build

```bash
cd custom-nodes/mistral/n8n-nodes-mistral-document-ai
npm i
npm run build
```

Build artifacts are generated in `dist/`.

## Load in n8n (Docker)

Add the following to your n8n service:

```yaml
services:
  n8n:
    environment:
      - N8N_CUSTOM_EXTENSIONS=/home/node/.n8n/custom
    volumes:
      - ./custom-nodes:/home/node/.n8n/custom
```

This keeps all existing runtime wiring intact and only adds custom extension loading.

## Smoke test

1. Rebuild/start container:

```bash
docker compose up -d --build
```

2. Confirm custom extension env is present:

```bash
docker compose exec n8n sh -lc 'echo $N8N_CUSTOM_EXTENSIONS'
```

3. In n8n UI, search for node: `Mistral Document AI`.

4. Build a quick workflow:
- `Google Drive` download node (binary output)
- `Mistral Document AI` node (`Binary Property Name` = your binary field, typically `data`)

5. Execute and verify output contains:
- `pages`
- `meta`
- optional `document_annotation`
- optional `raw` when enabled

## Per-page verification

No automated tests are included in this package. Use this manual harness:

1. Set `Pages` to `16-18`.
2. Set `Enable Document Annotation` to `true`.
3. Toggle `Annotate Per Page`:
   - `false`: expect one output item for the whole range.
   - `true`: expect three output items, each with:
     - `page_index` (`16`, `17`, `18`)
     - `page`
     - `document_annotation`
     - `meta.singlePage`
