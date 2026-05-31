---
phase: 03-entity-platforms
plan: "03"
subsystem: integration
tags: [platform-forwarding, entities, integration-tests, binary-sensor, sensor]
requires:
  - 03-02-SUMMARY.md
provides:
  - platform-forwarding
  - entity-integration-tests
affects:
  - custom_components/gatus/__init__.py
  - tests/test_entities.py
tech-stack:
  added: []
  patterns:
    - async_forward_entry_setups/async_unload_platforms for platform lifecycle
    - top-level import from custom_components.gatus to anchor namespace package in sys.modules
key-files:
  modified:
    - custom_components/gatus/__init__.py
  created:
    - tests/test_entities.py
decisions:
  - PLATFORMS constant exported from __init__.py for use by tests and documentation
  - Top-level import in test_entities.py required because HA loader's _async_mount_config_dir temporarily inserts testing_config dir into sys.path, which shadows our custom_components namespace package; importing from custom_components.gatus first anchors the correct module
  - HA normalizes entity IDs — hyphens in endpoint keys become underscores in entity_id (e.g. core_my-service → gatus_core_my_service_status); tests use underscored IDs
  - native_value=None in SensorEntity reports state as "unknown" (not "unavailable") in HA test environment; uptime sensor with no results asserts "unknown"
metrics:
  duration: ~30 minutes
  completed: "2026-05-31"
  tasks: 2
  files: 2
---

# Phase 03 Plan 03: Platform Forwarding & Integration Tests Summary

Wire `async_forward_entry_setups` / `async_unload_platforms` in `__init__.py` and add 8 integration tests verifying entity loading, attributes, and stale cleanup end-to-end.

## What Was Built

### Task 1: Platform Forwarding in `__init__.py`
- Added `PLATFORMS: list[str] = ["binary_sensor", "sensor"]` module-level constant
- `async_setup_entry` calls `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)` after setting `entry.runtime_data`
- `async_unload_entry` replaced with `return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)`
- Removed all Phase 1 stub comments; `PLATFORMS` exported in `__all__`

### Task 2: Integration Tests (`tests/test_entities.py`)
8 integration tests using `MockConfigEntry` + `aioclient_mock`:

| Test | Requirement |
|------|-------------|
| `test_binary_sensor_state_up` | SENS-01: binary sensor state "on" when success=True |
| `test_binary_sensor_attributes` | SENS-02..05: all 4 attributes present and correct |
| `test_binary_sensor_state_down` | SENS-01/03: state "off"; error_reason = first failing condition |
| `test_response_time_sensor` | SENS-06: response time sensor state = duration_ms |
| `test_uptime_sensor_none_when_no_results` | SENS-07: uptime sensor state "unknown" when no results |
| `test_conditions_sensor_xoy_string` | SENS-08: conditions state "2/3" with 3 conditions |
| `test_conditions_sensor_zero_when_no_conditions` | SENS-08: conditions state "0/0" with empty results |
| `test_stale_entity_removed` | DEVICE-04: stale entity removed from entity registry after coordinator refresh |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Entity ID normalization: hyphens become underscores**
- **Found during:** Task 2 TDD GREEN phase
- **Issue:** Plan interface example used `binary_sensor.gatus_core_my-service_status` (with hyphen). HA normalizes hyphens to underscores in entity IDs. Actual entity ID is `binary_sensor.gatus_core_my_service_status`
- **Fix:** Updated all test entity ID lookups to use underscores

**2. [Rule 1 - Bug] Uptime sensor with None native_value reports "unknown" not "unavailable"**
- **Found during:** Task 2 TDD GREEN phase
- **Issue:** Plan spec said state would be "unavailable". HA SensorEntity reports "unknown" when native_value=None
- **Fix:** Updated assertion to `assert state.state == "unknown"`

**3. [Rule 1 - Bug] Integration not found when test_entities.py runs standalone**
- **Found during:** Task 2 TDD RED phase
- **Root cause:** HA's `_async_mount_config_dir` temporarily inserts `testing_config` directory into `sys.path` and does `import custom_components`, which registers the plugin's `custom_components/__init__.py` (a regular package) in `sys.modules`. Subsequent calls to `_get_custom_components` find only the testing_config's custom components (not our `gatus` integration) because the namespace package is shadowed.
- **Fix:** Added top-level import `from custom_components.gatus.coordinator import GatusDataUpdateCoordinator` to `test_entities.py`. This runs at pytest collection time (before `_async_mount_config_dir` runs), anchoring our project's namespace package in `sys.modules` so it cannot be shadowed
- **Pattern:** Same pattern used by `test_init.py` which has top-level `from custom_components.gatus import ...` imports; this is now documented as a required pattern for test files that exercise the full HA integration lifecycle

## Decisions Made

1. **PLATFORMS constant exported** — `__all__` updated to include `PLATFORMS` for discoverability
2. **Top-level import required in test files** — All test files using `hass.config_entries.async_setup()` MUST have at least one top-level `from custom_components.gatus...` import to prevent the testing_config shadow issue
3. **HA entity ID normalization** — Entity IDs returned by `hass.states.get()` always use underscores; entity_ids set with hyphens are normalized automatically

## Test Results

- 8 new entity integration tests: all pass
- Full suite (48 tests): all pass
- ruff check: no errors

## Self-Check: PASSED

- custom_components/gatus/__init__.py: FOUND
- tests/test_entities.py: FOUND
- Commit 2bde4df (feat(03-03): wire platform forwarding): FOUND
- Commit 33fe260 (test(03-03): add entity integration tests): FOUND
