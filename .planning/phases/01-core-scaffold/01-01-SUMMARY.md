---
phase: 01-core-scaffold
plan: 01
subsystem: scaffold
tags: [constants, manifest, hacs, ruff, pytest, dev-toolchain]
dependency_graph:
  requires: []
  provides:
    - custom_components/gatus/const.py (DOMAIN, DEFAULT_SCAN_INTERVAL)
    - custom_components/gatus/manifest.json (integration metadata)
    - custom_components/gatus/__init__.py (stub — fully implemented in Plan 03)
    - pyproject.toml (pytest + mypy config)
    - .ruff.toml (ruff config)
    - hacs.json (HACS metadata)
    - uv.lock (dev dependency lockfile)
  affects: []
tech_stack:
  added:
    - ruff 0.15.15 (lint + format)
    - pytest 9.0.x (test runner)
    - pytest-homeassistant-custom-component 0.13.x (HA fixtures)
    - pytest-asyncio 1.x (async test support)
    - pytest-cov 7.x (coverage)
    - mypy 2.1.x (type checking)
  patterns:
    - uv for dev dependency management (pyproject.toml [dependency-groups])
    - ruff for lint/format via .ruff.toml (line-length 120, target py314)
key_files:
  created:
    - custom_components/gatus/const.py
    - custom_components/gatus/manifest.json
    - custom_components/gatus/__init__.py
    - custom_components/gatus/
    - hacs.json
    - pyproject.toml
    - .ruff.toml
    - tests/__init__.py
    - .gitignore
    - uv.lock
  modified: []
decisions:
  - "TypedDict preferred over dataclass for GatusEndpoint (Plan 02 scope)"
  - "documentation and issue_tracker added to manifest beyond D-09 spec (Pitfall 1 resolved)"
  - "GatusConfigEntry type alias uses Any in Phase 1 stub; narrowed to GatusDataUpdateCoordinator in Plan 03"
  - ".gitignore added as Rule 2 (missing critical dev hygiene)"
metrics:
  duration: "~10 minutes"
  completed: "2026-05-30T22:52:23Z"
  tasks_completed: 2
  files_created: 10
requirements_satisfied:
  - POLL-04
---

# Phase 1 Plan 1: Integration Scaffold Summary

Static integration scaffold: constants, manifest, HACS metadata, tool configuration, and a minimal __init__.py stub — the non-behavioral foundation that every subsequent plan imports or builds on.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Verify dev package legitimacy before install | (checkpoint — human verified) | — |
| 2 | Create scaffold files and install dev dependencies | 1dff1cc | const.py, manifest.json, __init__.py, hacs.json, pyproject.toml, .ruff.toml, tests/__init__.py, .gitignore, uv.lock |

## What Was Built

### custom_components/gatus/const.py
Defines `DOMAIN = "gatus"` and `DEFAULT_SCAN_INTERVAL = 60` (satisfies POLL-04).

### custom_components/gatus/manifest.json
All hassfest-required fields: domain, name, codeowners, config_flow, integration_type, iot_class, version, requirements, documentation, issue_tracker. Does NOT include quality_scale (hassfest warns on custom integrations).

### custom_components/gatus/__init__.py
Minimal stub that exports `DOMAIN` and the `GatusConfigEntry` type alias. `async_setup_entry` and `async_unload_entry` raise `NotImplementedError` with docstrings pointing to Plan 03. Uses `from __future__ import annotations` and `TYPE_CHECKING` guard to avoid HA imports at bare Python runtime.

### hacs.json
Declares homeassistant minimum `2025.1.0` and hacs minimum `2.0.5`. Standard folder-based distribution (no `filename` field needed).

### pyproject.toml
`[project]` table with `requires-python = ">=3.14"`. `[tool.pytest.ini_options]` with `asyncio_mode = "auto"` and `testpaths = ["tests"]`. `[tool.mypy]` with `python_version = "3.14"` and `strict = true`. `[dependency-groups]` populated by `uv add --dev`.

### .ruff.toml
`line-length = 120`, `target-version = "py314"`. Separate from pyproject.toml to avoid duplicate config.

### Dev toolchain
Installed via `uv add --dev`: pytest, pytest-homeassistant-custom-component, pytest-asyncio, pytest-cov, ruff, mypy. `uv.lock` committed for reproducibility.

## Verification Results

All acceptance criteria passed:

- `custom_components/gatus/const.py` exports `DOMAIN = "gatus"` and `DEFAULT_SCAN_INTERVAL = 60` — PASS
- `manifest.json` valid JSON with all required hassfest fields (including documentation, issue_tracker) — PASS
- `manifest.json` does NOT contain quality_scale — PASS
- `hacs.json` contains `homeassistant: "2025.1.0"` and `hacs: "2.0.5"` — PASS
- `pyproject.toml` contains `asyncio_mode = "auto"` under `[tool.pytest.ini_options]` — PASS
- `.ruff.toml` contains `line-length = 120` — PASS
- `ruff check custom_components/gatus/` exits 0 — PASS
- `uv run python -c "import pytest"` exits 0 — PASS
- `custom_components/gatus/__init__.py` contains `from .const import DOMAIN` — PASS

## Deviations from Plan

### Auto-added (Rule 2 - Missing Critical Functionality)

**1. [Rule 2 - Missing Dev Hygiene] Added .gitignore**
- **Found during:** Post-install check (uv created .venv/ and .cache/ directories)
- **Issue:** No .gitignore existed; `.venv/`, `__pycache__/`, `.pytest_cache/` would be accidentally committed
- **Fix:** Created `.gitignore` with standard Python/HA dev exclusions
- **Files modified:** `.gitignore` (new)
- **Commit:** 1dff1cc

**2. [Rule 2 - Ruff F401 prevention] Added `__all__` to `__init__.py`**
- **Found during:** Pre-write analysis (advisor flagged F401 risk on unused `DOMAIN` import)
- **Issue:** `from .const import DOMAIN` would trigger ruff F401 (unused import) if not re-exported
- **Fix:** Added `__all__ = ["DOMAIN", "GatusConfigEntry"]` and `# noqa: F401` comment
- **Commit:** 1dff1cc

**3. [Rule 2 - Runtime safety] TYPE_CHECKING guard in `__init__.py`**
- **Found during:** Pre-write analysis (advisor flagged bare python import failure risk)
- **Issue:** `from homeassistant.config_entries import ConfigEntry` at module level fails when HA is not installed (bare python -c verify commands)
- **Fix:** Guarded HA imports under `if TYPE_CHECKING:` with `from __future__ import annotations`
- **Commit:** 1dff1cc

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `async_setup_entry` raises NotImplementedError | `custom_components/gatus/__init__.py` | Requires coordinator.py (Plan 02) and platform setup (Plan 03) |
| `async_unload_entry` raises NotImplementedError | `custom_components/gatus/__init__.py` | Requires platform teardown (Plan 03) |
| `GatusConfigEntry = ConfigEntry[Any]` | `custom_components/gatus/__init__.py` | Narrowed to `ConfigEntry[GatusDataUpdateCoordinator]` in Plan 03 |

These stubs are intentional — this plan establishes the static scaffold only. Plans 02 and 03 implement the behavioral layer.

## Threat Flags

No new security surface introduced. The `codeowners: ["@akentner"]` field in manifest.json exposes a GitHub username — accepted per T-01-01 (GitHub username is public). No user input, no HTTP calls, no network surface in this plan.

## Self-Check: PASSED

- `custom_components/gatus/const.py` — FOUND
- `custom_components/gatus/manifest.json` — FOUND
- `custom_components/gatus/__init__.py` — FOUND
- `hacs.json` — FOUND
- `pyproject.toml` — FOUND
- `.ruff.toml` — FOUND
- `tests/__init__.py` — FOUND
- Commit 1dff1cc — FOUND
