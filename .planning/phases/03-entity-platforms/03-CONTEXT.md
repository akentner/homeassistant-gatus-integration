# Phase 3: Entity Platforms - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Entity platforms: binary_sensor + three sensor types (response time, uptime %, conditions) for every Gatus endpoint. Device grouping by Gatus group name. Stale entity cleanup when endpoints disappear. No new API calls beyond what the coordinator already fetches.

Requirements in scope: SENS-01, SENS-02, SENS-03, SENS-04, SENS-05, SENS-06, SENS-07, SENS-08, DEVICE-01, DEVICE-02, DEVICE-03, DEVICE-04

</domain>

<decisions>
## Implementation Decisions

### Consecutive Failures (SENS-05)
- **D-01:** Compute `consecutive_failures` by scanning `results[]` in order (newest first) and counting leading `success=false` entries until the first `success=true`. Uses the results array already stored in `coordinator.data` — no extra API calls. Value caps at the length of the results array (typically 20 from Gatus). This is acceptable for v1.

### Uptime % (SENS-07)
- **D-02:** Compute uptime % from the `results[]` array already returned by `GET /api/v1/endpoints/statuses`. Formula: `success_count / len(results) * 100`. No `?duration` query param added. The open concern in STATE.md is resolved in favour of simplicity: use what's in the coordinator data.
- **D-03:** If `results[]` is empty, uptime % is `None` (entity unavailable), not 0.

### Conditions Sensor (SENS-08)
- **D-04:** State = `"X/Y"` string (passed/total conditions). Additionally, expose a `condition_details` attribute as a list of `{condition: str, success: bool}` dicts, sourced from `conditionResults[]` already in `coordinator.data[endpoint_key]["condition_results"]`. This carries the full breakdown at no extra API cost.

### Stale Entity Cleanup (DEVICE-04)
- **D-05:** Register a coordinator update listener in each platform's `async_setup_entry`. On each coordinator refresh, compare `coordinator.data` keys against the entity registry entries for this config entry. Remove any entity whose `endpoint_key` is absent from the fresh data. Use `entity_registry.async_remove(entity_id)` for immediate removal.
- **D-06:** Removal is immediate on first missing refresh — no N-miss grace period. Gatus API is reliable; transient blips cause coordinator `UpdateFailed` (entity becomes unavailable), not an empty dict.

### Platform File Structure
- **D-07:** Three files: `binary_sensor.py`, `sensor.py`, and a shared base module. The shared base can be an internal module (e.g., `entity.py` or inline base class pattern) — agent's discretion on exact file name. `binary_sensor.py` and `sensor.py` are the HA platform entry points; both import the shared base.

### Binary Sensor Attributes (SENS-02, SENS-03, SENS-04, SENS-05)
- **D-08:** Binary sensor carries exactly these attributes:
  - `last_check_timestamp`: ISO 8601 string from `results[0]["timestamp"]`
  - `error_reason`: first failing condition's `condition` string, or `None` if up
  - `response_duration_ms`: `duration_ms` from coordinator data (already in ms)
  - `consecutive_failures`: computed per D-01

### Agent's Discretion
- Exact name of the shared base file (`entity.py`, `base.py`, or inline in one platform file)
- Whether `error_reason` extracts from `condition_results` list or from a helper function
- Whether uptime % is rounded (e.g., 2 decimal places) or raw float

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements
- `.planning/REQUIREMENTS.md` — Full requirement list; Phase 3 scope: SENS-01..SENS-08, DEVICE-01..DEVICE-04
- `.planning/ROADMAP.md` §Phase 3 — Success criteria
- `.planning/PROJECT.md` §Key Decisions — Locked architectural decisions

### HA Integration Conventions (from CLAUDE.md)
- `CLAUDE.md` §Architecture Libraries — Import paths for SensorEntity, BinarySensorEntity, CoordinatorEntity, DeviceInfo, BinarySensorDeviceClass
- `CLAUDE.md` §HA Integration Conventions — Unique ID format, entity object ID format, CoordinatorEntity pattern
- `CLAUDE.md` §What NOT to Use — Banned patterns

### Existing Phase 1 & 2 Code (MUST READ)
- `custom_components/gatus/coordinator.py` — `GatusEndpoint` TypedDict shape: key, name, group, success, duration_ms, timestamp, condition_results. This is the exact data contract entities consume.
- `custom_components/gatus/__init__.py` — `GatusConfigEntry` type alias; `async_setup_entry` needs `async_forward_entry_setups` added for `binary_sensor` and `sensor` platforms in Phase 3.
- `custom_components/gatus/const.py` — `DOMAIN`, `DEFAULT_PREFIX`

### Prior Phase Decisions
- `.planning/phases/01-core-scaffold/01-CONTEXT.md` §D-01, D-02 — coordinator.data dict shape and disappearing endpoint contract
- `.planning/phases/02-config-flow/02-CONTEXT.md` §D-03, D-05 — `entry.data["prefix"]` key name; prefix is set-once

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GatusEndpoint` TypedDict in `coordinator.py` — direct input to all 4 entity types. Fields already computed: `success` (bool), `duration_ms` (int, already in ms), `timestamp` (str), `condition_results` (list[dict]).
- `GatusConfigEntry = ConfigEntry[GatusDataUpdateCoordinator]` type alias in `__init__.py` — use as the typed entry parameter in platform setup functions.
- `DEFAULT_PREFIX = "gatus_"` in `const.py`

### Established Patterns
- `entry.runtime_data` holds the coordinator — access via `entry.runtime_data` in platform `async_setup_entry`.
- `entry.data["prefix"]` is the entity object ID prefix established in Phase 2.
- Entity unique IDs: `{entry.entry_id}_{endpoint_key}_{sensor_type}` (DEVICE-02).
- Entity object IDs: `{prefix}{endpoint_key}_{sensor_type}` (DEVICE-03).

### Integration Points
- `__init__.py` `async_setup_entry` must call `await hass.config_entries.async_forward_entry_setups(entry, ["binary_sensor", "sensor"])` (currently omitted with Phase 1 stub comment).
- `__init__.py` `async_unload_entry` must call `await hass.config_entries.async_unload_platforms(entry, ["binary_sensor", "sensor"])`.
- Each platform's `async_setup_entry` receives the `GatusConfigEntry` and calls `async_add_entities` with initial entity list, then registers the coordinator update listener for stale cleanup (D-05).

</code_context>

<specifics>
## Specific Ideas

- `consecutive_failures`: iterate `coordinator.data[key]["condition_results"]` is wrong — use the `results[]` array. But `GatusEndpoint` only stores `results[0]` fields. **Note for planner**: the coordinator currently only parses `results[0]` into the TypedDict. To compute consecutive_failures, either (a) store the full `results[]` list in `GatusEndpoint` (add a `results` field), or (b) compute it in `_parse_endpoint` and add a `consecutive_failures: int` field directly to the TypedDict. Option (b) is cleaner — compute once in coordinator, expose as attribute in entity.
- Uptime % computation also needs the full results list or a pre-computed field. Same approach: add `uptime_pct: float | None` to `GatusEndpoint` computed in `_parse_endpoint`.
- This means Phase 3 will need a minor coordinator extension: add `consecutive_failures` and `uptime_pct` fields to `GatusEndpoint` and compute them in `_parse_endpoint`. The coordinator unit tests from Phase 1 will need updating.

</specifics>

<deferred>
## Deferred Ideas

- **Summary/aggregate sensor**: One sensor per config entry showing % of green endpoints, with `healthy_endpoints` and `unhealthy_endpoints` attribute lists. Not in REQUIREMENTS.md — belongs in a future phase.

</deferred>

---

*Phase: 03-entity-platforms*
*Context gathered: 2026-05-31*
