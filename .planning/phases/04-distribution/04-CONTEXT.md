---
phase: 04
name: Distribution
date: 2026-05-31
status: ready-to-plan
---

# Phase 04: Distribution — Context

## Domain

Make the integration installable via HACS and ensure all required files pass HACS and HA validator checks. This phase does not add new integration functionality — it packages and validates what was built in phases 1–3.

## Canonical References

- `.planning/REQUIREMENTS.md` — DIST-01, DIST-02 requirements
- `.planning/ROADMAP.md` — Phase 4 success criteria
- `custom_components/gatus/manifest.json` — already correct, needs verification
- `hacs.json` — already correct, needs verification
- HACS integration requirements: https://hacs.xyz/docs/publish/integration/
- HACS GitHub Action: https://hacs.xyz/docs/publish/action/

## Decisions

### README
- **What:** Create `README.md` at repo root
- **Scope:** Installation (HACS + manual SCP), Config Flow fields (URL, API key, entity_id prefix, scan interval), entity list per Gatus endpoint (binary sensor + 3 sensors with descriptions and attributes)
- **Why:** HACS `information` check requires an information file (README.md)

### Brand Assets
- **What:** Create `brand/icon.png` (256×256)
- **Source:** Download Gatus logo from `https://github.com/TwiN/gatus/blob/master/web/static/logo-512x512.png?raw=true` and resize to 256×256
- **Why:** HACS `brands` check; using the official Gatus logo is appropriate since this integration wraps Gatus
- **Tool:** `python` with `PIL`/`Pillow` (or `convert` from ImageMagick if available) to resize

### GitHub Actions Validation
- **What:** Create `.github/workflows/validate.yml` with two jobs:
  1. HACS validation via `hacs/action@main` with `category: integration`
  2. hassfest validation via the official hassfest action (`hacs/action@main` tip links to hassfest blog)
- **Triggers:** push, pull_request, schedule (daily at midnight), workflow_dispatch
- **Brands check:** Do NOT ignore — icon.png will be provided

### Validation Approach
- Manual field-by-field check of `manifest.json` and `hacs.json` against requirements
- GitHub Actions CI enforces ongoing compliance (hassfest + HACS action)
- No local hassfest run needed — CI is sufficient

## Code Context

- `custom_components/gatus/manifest.json` — all required HACS fields already present: domain, name, codeowners, config_flow, integration_type, iot_class, version, documentation, issue_tracker
- `hacs.json` — already has name, homeassistant: "2025.1.0", hacs: "2.0.5"
- Repository structure is correct: `custom_components/gatus/` at root with all integration files
- No third-party pip requirements — `requirements: []` in manifest

## Out of Scope

- Submitting to HACS default repositories (that's a separate manual process after v1.0)
- Creating GitHub releases/tags (deferred)
- Writing contributing guidelines
