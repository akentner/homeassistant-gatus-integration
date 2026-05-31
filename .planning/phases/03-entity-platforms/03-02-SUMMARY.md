---
phase: 03-entity-platforms
plan: "02"
subsystem: entity-platforms
tags: [binary_sensor, sensor, entities, stale-cleanup]
dependency_graph:
  requires: [03-01]
  provides: [binary_sensor.py, sensor.py]
  affects: [__init__.py]
tech_stack:
  added: []
  patterns: [CoordinatorEntity subclass, stale-entity cleanup via entity_registry]
key_files:
  created:
    - custom_components/gatus/binary_sensor.py
    - custom_components/gatus/sensor.py
  modified: []
decisions:
  - "GatusConditionsSensor native_value is 'X/Y' string (not int) — matches SENS-08 spec"
  - "Stale cleanup strips sensor_type suffix from unique_id to recover endpoint_key"
metrics:
  duration: "~1 minute"
  completed: "2026-05-31"
  tasks_completed: 2
  files_created: 2
---

# Phase 03 Plan 02: Entity Platforms (binary_sensor + sensor) Summary

**One-liner:** Four Gatus entity classes (BinarySensor + 3 sensors) wired to CoordinatorEntity with stale-endpoint cleanup on every coordinator refresh.

## What Was Built

### binary_sensor.py
- `GatusBinarySensorEntity(GatusEntity, BinarySensorEntity)` — `BinarySensorDeviceClass.CONNECTIVITY`
- `is_on` mirrors `endpoint["success"]`
- `extra_state_attributes`: `last_check_timestamp`, `error_reason` (first failing condition or None), `response_duration_ms`, `consecutive_failures`
- `async_setup_entry` creates one entity per coordinator key + registers stale-cleanup listener

### sensor.py
- `GatusResponseTimeSensor` — `duration_ms` int, `SensorDeviceClass.DURATION`, unit `ms`, `SensorStateClass.MEASUREMENT`
- `GatusUptimeSensor` — `uptime_pct` float|None, unit `%`, `SensorStateClass.MEASUREMENT`, no device_class
- `GatusConditionsSensor` — `native_value` = `"X/Y"` string; `extra_state_attributes["condition_details"]` = list of `{condition, success}` dicts
- `async_setup_entry` creates 3 entities per endpoint key + registers stale-cleanup listener

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 — binary_sensor.py | `6d4f467` | feat(03-02): implement GatusBinarySensorEntity with stale cleanup |
| 2 — sensor.py | `4e87db1` | feat(03-02): implement 3 sensor entities with stale cleanup |

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all data flows from coordinator through `_endpoint` accessor.

## Self-Check: PASSED

- `custom_components/gatus/binary_sensor.py` — EXISTS ✓
- `custom_components/gatus/sensor.py` — EXISTS ✓
- Commit `6d4f467` — EXISTS ✓
- Commit `4e87db1` — EXISTS ✓
