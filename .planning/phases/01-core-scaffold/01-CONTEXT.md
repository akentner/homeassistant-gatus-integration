# Phase 1: Core Scaffold - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

DataUpdateCoordinator, `__init__.py`, and constants — the data pipeline that Phase 3 entities consume. No entities in this phase. Goal: a loadable HA integration that polls Gatus endpoints, stores data in coordinator, handles errors correctly, and cleans up on unload.

Requirements in scope: POLL-01, POLL-02, POLL-03, POLL-04

</domain>

<decisions>
## Implementation Decisions

### Coordinator Data Structure
- **D-01:** `coordinator.data` is a `Dict[str, <typed structure>]` keyed by `endpoint_key` (raw from Gatus API, e.g. `core_my-service`). Claude chooses the best typed structure (TypedDict or dataclass) per HA conventions.
- **D-02:** When an endpoint disappears from the API response, its key is removed from `coordinator.data`. This enables Phase 3 active reconciliation (DEVICE-04).

### HTTP Error Handling
- **D-03:** HTTP 401/403 → raise `ConfigEntryAuthFailed`. Triggers HA re-auth flow. Correct signal for bad API key.
- **D-04:** Network errors (timeout, connection refused) and non-auth HTTP errors → raise `UpdateFailed` (for subsequent refreshes). Only on the FIRST refresh does a network error become `ConfigEntryNotReady`.
- **D-05:** HTTP 200 with invalid/unparseable JSON → raise `UpdateFailed` with error message logged. Do not silently return empty dict.

### Test Coverage
- **D-06:** Test both Coordinator and `__init__.py` (setup/unload) in Phase 1.
- **D-07:** Mandatory test cases:
  1. Successful fetch — `coordinator.data` has correct shape keyed by `endpoint_key`
  2. First-refresh network failure → `ConfigEntryNotReady` raised
  3. 401/403 response → `ConfigEntryAuthFailed` raised
  4. Integration setup and unload are clean — no stale `entry.runtime_data`

### manifest.json
- **D-08:** Finalize manifest.json completely in Phase 1 (all hassfest-required fields). Phase 4 validates, does not change.
- **D-09:** Fields: `domain: gatus`, `name: Gatus`, `codeowners: ["@akentner"]`, `config_flow: true`, `integration_type: hub`, `iot_class: cloud_polling`, `version: "0.1.0"`, `requirements: []`.

### Claude's Discretion
- Internal data structure type (TypedDict vs dataclass) — Claude picks best HA pattern.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements
- `.planning/REQUIREMENTS.md` — Full requirement list with IDs; Phase 1 scope: POLL-01..POLL-04
- `.planning/ROADMAP.md` §Phase 1 — Success criteria and dependency order
- `.planning/PROJECT.md` §Key Decisions — Locked architectural decisions (coordinator pattern, runtime_data, aiohttp session)

### HA Integration Conventions (from CLAUDE.md)
- `CLAUDE.md` §Architecture Libraries — Import paths for DataUpdateCoordinator, CoordinatorEntity, ConfigEntryNotReady, ConfigEntryAuthFailed, async_get_clientsession
- `CLAUDE.md` §What NOT to Use — Banned patterns (httpx, requests, async_timeout module, hass.data[DOMAIN])

### Gatus API
- `CLAUDE.md` §Gatus API — Endpoint structure, key/name/group/results fields, auth header format

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project. No existing code to reuse.

### Established Patterns
- HA `DataUpdateCoordinator` + `CoordinatorEntity` pattern: standard for polling integrations. Single HTTP call per interval, all entities subscribe.
- `entry.runtime_data` for storing coordinator reference (replaces deprecated `hass.data[DOMAIN][entry_id]`).
- `async_get_clientsession(hass)` — shared aiohttp session, never create own ClientSession.

### Integration Points
- Phase 1 output (`coordinator.data` shape) is the contract consumed by Phase 3 sensor entities.
- `__init__.py` `async_setup_entry` / `async_unload_entry` are the HA lifecycle hooks.

</code_context>

<specifics>
## Specific Ideas

- Gatus API returns duration in nanoseconds — divide by 1,000,000 to get milliseconds (already locked in STATE.md).
- Uptime % data source: `results` array from statuses endpoint. Verify `?duration` query param behavior against live Gatus before Phase 3 (open concern in STATE.md).

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Core Scaffold*
*Context gathered: 2026-05-31*
