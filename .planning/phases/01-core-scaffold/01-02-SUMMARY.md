---
phase: 01-core-scaffold
plan: 02
subsystem: coordinator
tags: [coordinator, tdd, polling, error-classification, data-update-coordinator]
dependency_graph:
  requires:
    - custom_components/gatus/const.py (DOMAIN, DEFAULT_SCAN_INTERVAL)
  provides:
    - custom_components/gatus/coordinator.py (GatusEndpoint TypedDict, GatusDataUpdateCoordinator)
    - tests/conftest.py (enable_custom_integrations fixture)
    - tests/test_coordinator.py (9 coordinator-level tests including D-02 disappearing endpoint)
  affects:
    - custom_components/gatus/__init__.py (Plan 03 will import GatusDataUpdateCoordinator)
    - custom_components/gatus/sensor.py (Phase 3: CoordinatorEntity wired to coordinator.data)
tech_stack:
  added: []
  patterns:
    - DataUpdateCoordinator[dict[str, GatusEndpoint]] for single-poll coordinator pattern
    - TypedDict for typed endpoint data contract (no dataclass overhead)
    - asyncio.timeout(10) (stdlib, not deprecated async_timeout)
    - aioclient_mock side_effect pattern for multi-response test sequencing
key_files:
  created:
    - custom_components/gatus/coordinator.py
    - tests/conftest.py
    - tests/test_coordinator.py
  modified: []
decisions:
  - "AiohttpClientMocker does not consume mocks on match — used side_effect callback for multi-response Test 9 (D-02)"
  - "async_add_listener cancel() required in Test 8 to prevent lingering polling timer at teardown"
  - "condition_results typed as list[dict[str, object]] (mypy strict — no bare dict)"
  - "D-02 (disappearing endpoint) implemented implicitly: _async_update_data returns fresh dict from API response only"
metrics:
  duration: "~7 minutes"
  completed: "2026-05-30T22:59:48Z"
  tasks_completed: 2
  files_created: 3
requirements_satisfied:
  - POLL-01
  - POLL-02
  - POLL-03
  - POLL-04
---

# Phase 1 Plan 2: GatusDataUpdateCoordinator Summary

GatusDataUpdateCoordinator using TDD: 9 failing tests committed (RED), then coordinator.py implemented to make all 9 pass (GREEN). Covers successful fetch, header injection, all error classifications (401/403/network/bad-JSON), scheduled re-fetch at 60 s, and D-02 disappearing endpoint.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 (RED) | Write failing tests for GatusDataUpdateCoordinator | 28784eb | tests/conftest.py, tests/test_coordinator.py |
| 2 (GREEN) | Implement coordinator.py to pass all tests | 95de6c4 | custom_components/gatus/coordinator.py (+ test updates) |

## TDD Gate Compliance

- RED gate commit: `28784eb` (test(01-02): add failing tests for GatusDataUpdateCoordinator)
- GREEN gate commit: `95de6c4` (feat(01-02): implement GatusDataUpdateCoordinator)
- REFACTOR gate: not required (code was clean from first implementation)

## What Was Built

### custom_components/gatus/coordinator.py

`GatusEndpoint` TypedDict — the data contract between the coordinator and all sensor entities. Fields: `key`, `name`, `group`, `success`, `duration_ms`, `timestamp`, `condition_results`.

`GatusDataUpdateCoordinator` extends `DataUpdateCoordinator[dict[str, GatusEndpoint]]`. Single polling point: calls `GET /api/v1/endpoints/statuses` once per `scan_interval` seconds using `async_get_clientsession(hass)`. Returns a fresh dict keyed by raw endpoint_key — absent endpoints are simply not included (D-02 implemented implicitly).

Error classification:
- HTTP 401/403 → `ConfigEntryAuthFailed` (triggers re-auth flow in HA)
- Any other HTTP error or network exception → `UpdateFailed`
- Unparseable JSON → `UpdateFailed("Invalid JSON from Gatus: ...")`
- `ConfigEntryNotReady` is NEVER raised here; the auto-conversion happens in `async_config_entry_first_refresh()` (Plan 03)

Security: `api_key` never logged; `Authorization` header only included when `api_key` is truthy.

### tests/conftest.py

`enable_custom_integrations` fixture (autouse=True) required by `pytest-homeassistant-custom-component`. Also ensures `custom_components/` is importable via `sys.path`.

### tests/test_coordinator.py

9 tests covering all plan-specified cases. Error-path tests (4–7) call `_async_update_data()` directly inside `pytest.raises()` — not `async_refresh()` — because `DataUpdateCoordinator` swallows `UpdateFailed`/`ConfigEntryAuthFailed` internally during `async_refresh()`.

## Verification Results

- `pytest tests/test_coordinator.py -v` exits 0 — 9/9 tests PASS
- `ruff check custom_components/gatus/coordinator.py` exits 0
- `mypy custom_components/gatus/coordinator.py` exits 0 (strict mode, no warnings)

## Deviations from Plan

### Auto-fixed Issues (Rule 1 - Bugs found during GREEN phase)

**1. [Rule 1 - Bug] Test 8 lingering timer at teardown**
- **Found during:** First test run (GREEN phase)
- **Issue:** `coordinator.async_add_listener()` arms HA's polling scheduler. Without cancelling the listener, the timer remains active at test teardown, causing `pytest_homeassistant_custom_component` `verify_cleanup` fixture to fail.
- **Fix:** Saved the cancel function returned by `async_add_listener()` and called `cancel()` at end of Test 8.
- **Files modified:** `tests/test_coordinator.py`
- **Commit:** 95de6c4

**2. [Rule 1 - Bug] Test 9 always returned first mock response**
- **Found during:** First test run (GREEN phase)
- **Issue:** `AiohttpClientMocker.match_request()` always matches the first registered mock for a URL — it does NOT consume/pop matched mocks. Registering two `get()` calls for the same URL does not create a response queue.
- **Fix:** Replaced two `aioclient_mock.get()` calls with a single `side_effect` callback that uses a `nonlocal` counter to return different `AiohttpClientMockResponse` objects per call.
- **Files modified:** `tests/test_coordinator.py`
- **Commit:** 95de6c4

**3. [Rule 1 - Bug] Mypy strict mode: bare `dict` type annotations**
- **Found during:** Post-implementation lint/type check
- **Issue:** `dict` without type args triggers `[type-arg]` errors under `mypy --strict`.
- **Fix:** Changed to `dict[str, object]` throughout `coordinator.py`; `_parse_endpoint` uses runtime isinstance checks before narrowing types.
- **Files modified:** `custom_components/gatus/coordinator.py`
- **Commit:** 95de6c4

## Known Stubs

None — coordinator is fully implemented. All 9 behavioral contracts are covered by passing tests.

## Threat Flags

No new security surface beyond plan's threat model. T-02-01 (api_key logging) mitigated: `self._api_key` is never logged; only the header name is logged if needed. T-02-02 (JSON tampering) mitigated: `resp.json(content_type=None)` wrapped in try/except; `isinstance(raw_list, list)` check before iteration.

## Self-Check: PASSED

- `custom_components/gatus/coordinator.py` — FOUND
- `tests/conftest.py` — FOUND
- `tests/test_coordinator.py` — FOUND
- Commit 28784eb (RED) — FOUND
- Commit 95de6c4 (GREEN) — FOUND
