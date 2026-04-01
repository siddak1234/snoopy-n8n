# Changelog

All notable changes to the Autom8x (A8X) n8n backend are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Sub-workflow modularization for shared pipeline stages
- CI/CD pipeline for automated testing and deployment
- Multi-client namespacing for tenant isolation

## [1.2.0] - 2026-03

### Changed
- Migrated LLM provider from Mistral to Gemini (Google AI Studio, direct API key)
- Updated all prompt templates and schema definitions for Gemini compatibility
- Removed all Mistral-related credentials, nodes, and configuration

### Added
- Live client deployment for invoice processing pipeline
- JSON schema validation layer for Gemini extraction output
- GCS folder restructure for client-namespaced storage paths

### Removed
- Mistral API integration and associated credentials
- Legacy prompt templates targeting Mistral models

## [1.1.0] - 2026-02

### Added
- Email ingestion pipeline (Gmail trigger → PDF extraction → GCS → downstream trigger)
- Gmail trigger node configuration for monitored inbox
- PDF attachment extraction and GCS upload workflow
- Downstream workflow trigger for chaining email ingestion to invoice processing

## [1.0.0] - 2026-01

### Added
- Initial invoice/receipt processing pipeline
- PDF upload and GCS storage integration
- LLM-powered OCR and line-item extraction (Mistral)
- GL code assignment logic
- Strict JSON schema output format
- Docker Compose overlay pattern (base, local, prod, gcp)
- Custom n8n image with pdf-lib 1.17.1
- SQLite persistence with volume mounts
- Operational scripts (up, down, logs, smoke-cleanup)
- Environment variable templates (.env.example, .env.local.example, .env.prod.example)
- Google Cloud ADC support (3 modes: generic VM, local JSON key, GCP metadata)
