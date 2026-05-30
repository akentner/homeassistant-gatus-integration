---
phase: 02-config-flow
plan: "01"
subsystem: config-flow
tags: [config-flow, tdd, validation, ui-setup]
dependency_graph:
  requires: []
  provides: [GatusConfigFlow.async_step_user, _validate_gatus_connection]
  affects: [02-02-reauth-reconfigure, 02-03-options-flow]
tech_stack:
  added: []
  patterns: [tdd-red-green, shared-validation-helper, voluptuous-selector]
key_files:
  created:
    - custom_components/gatus/strings.json
    - custom_components/gatus/translations/en.json
    - tests/test_config_flow.py
  modified:
    - custom_components/gatus/config_flow.py
    - custom_components/gatus/const.py
decisions:
  - "Shared _validate_gatus_connection helper is module-level (not inner class) for reuse by Reconfigure/Reauth flows (D-02)"
  - "Empty API key string normalized to None before storage — prevents empty-string vs None inconsistency downstream"
  - "asyncio.timeout(10) used (not deprecated async_timeout module)"
metrics:
  duration: "~15 minutes"
  completed: "2026-05-31"
  tasks: 2
  files: 5
---

# Phase 02 Plan 01: Config Flow User Step Summary

**One-liner:** JWT-free URL+API key config flow with shared validation helper, duplicate detection, and 7 TDD-verified test cases.

## What Was Built

Implemented the core Config Flow `async_step_user` and shared `_validate_gatus_connection` helper for the Gatus HA integration. Users can now add a Gatus instance through the HA UI by entering a URL, optional API key, and optional entity prefix. The flow validates connectivity, normalizes inputs, and detects duplicates before saving the config entry.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Validation helper + async_step_user (TDD) | 12656b4 | config_flow.py, const.py, test_config_flow.py |
| 2 | Config Flow strings and translations | 118613d | strings.json, translations/en.json |

## Decisions Made

1. **Shared `_validate_gatus_connection` helper** — module-level async function (not inline) per D-02. Reusable by Plan 02 Reconfigure and Reauth flows without duplication.
2. **Empty string → None normalization** for API key before storage prevents downstream inconsistency between `""` and `None` in coordinator.
3. **`asyncio.timeout(10)`** used for HTTP timeout (stdlib, not deprecated `async_timeout` module per CLAUDE.md).
4. **Unique ID** is the lowercased URL — enables HA's built-in duplicate detection via `_abort_if_unique_id_configured`.
5. **Entry title** is `urlparse(url).hostname` — hostname only, no user-supplied name field (D-06).

## Test Coverage

7 tests covering:
- Happy path (200 response, default prefix, scan_interval in options)
- `cannot_connect` error (ClientError raised)
- `invalid_auth` error (401 response)
- Duplicate URL abort (`already_configured`)
- Custom prefix stored correctly
- Empty prefix falls back to `DEFAULT_PREFIX = "gatus_"`
- Trailing slash stripped from URL before storage

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `custom_components/gatus/config_flow.py` — exists ✓
- `custom_components/gatus/const.py` — DEFAULT_PREFIX, MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL added ✓
- `custom_components/gatus/strings.json` — exists ✓
- `custom_components/gatus/translations/en.json` — exists, matches strings.json ✓
- `tests/test_config_flow.py` — 7 tests, all passing ✓
- Commits 12656b4, 118613d — both present in git log ✓
