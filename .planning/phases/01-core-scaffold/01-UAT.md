---
status: complete
phase: 01-core-scaffold
source: [01-01-SUMMARY.md, 01-02-SUMMARY.md, 01-03-SUMMARY.md]
started: 2026-05-31T00:00:00Z
updated: 2026-05-31T00:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Full test suite passes
expected: Run `uv run pytest tests/ -v` — 15/15 tests pass, 0 failures, 0 errors.
result: pass

### 2. Lint clean
expected: Run `uv run ruff check custom_components/gatus/` — exits 0, no violations reported.
result: pass

### 3. Type check clean
expected: Run `uv run mypy custom_components/gatus/` — exits 0, "Success: no issues found" with strict mode.
result: pass

### 4. Manifest valid
expected: `manifest.json` contains domain, name, codeowners, config_flow, integration_type, iot_class, version, requirements, documentation, issue_tracker. Does NOT contain quality_scale. Valid JSON.
result: pass

### 5. HACS metadata valid
expected: `hacs.json` contains `homeassistant: "2025.1.0"` and `hacs: "2.0.5"`. No filename field. Valid JSON.
result: pass

### 6. Coordinator polls Gatus API
expected: `coordinator.py` exports `GatusDataUpdateCoordinator`. After `async_refresh()` against a mocked Gatus endpoint, `coordinator.data` is a dict keyed by endpoint key (`"group_name"` format) with `GatusEndpoint` TypedDicts containing `key`, `name`, `group`, `success`, `duration_ms`, `timestamp`, `condition_results`.
result: pass

### 7. Auth failure raises correct exception
expected: When Gatus API returns HTTP 401 or 403, `_async_update_data()` raises `ConfigEntryAuthFailed` (not UpdateFailed). This is covered by coordinator tests 4 and 5.
result: pass

### 8. Network/parse failure causes SETUP_RETRY
expected: When a network error or invalid JSON occurs on first refresh, `async_setup_entry` raises `ConfigEntryNotReady` (via `async_config_entry_first_refresh` auto-conversion). HA retries setup automatically. Covered by test_init.py Test 5.
result: pass

### 9. Integration loads and unloads cleanly
expected: `async_setup_entry` creates coordinator, calls first refresh, assigns `entry.runtime_data` only on success. `async_unload_entry` returns True. No lingering state on unload. Reload creates a fresh coordinator object (id() differs). Covered by test_init.py Tests 1–3.
result: pass

### 10. Dev toolchain works from scratch
expected: After `git clone` + `uv sync`, running `uv run pytest tests/` completes without manual pip installs. `uv.lock` is committed and pins all dev deps reproducibly.
result: pass

## Summary

total: 10
passed: 10
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
