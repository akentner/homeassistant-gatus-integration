---
phase: 260531-g5q-group-binary-sensors
plan: 01
subsystem: entity-platforms
tags: [binary_sensor, group, sensor, cleanup]
dependency_graph:
  requires: []
  provides: [GatusGroupBinarySensor, group-health-entity]
  affects: [binary_sensor.py, sensor.py, tests/test_entities.py]
tech_stack:
  added: []
  patterns: [CoordinatorEntity+BinarySensorEntity direct inheritance for non-per-endpoint entities]
key_files:
  created: []
  modified:
    - custom_components/gatus/binary_sensor.py
    - custom_components/gatus/sensor.py
    - tests/test_entities.py
decisions:
  - GatusGroupBinarySensor extends CoordinatorEntity+BinarySensorEntity directly (not GatusEntity) — group sensors are not per-endpoint
  - Stale cleanup checks both _status and _group uid suffixes with defensive guard
metrics:
  duration: "~8 minutes"
  completed: "2026-05-31"
  tasks: 2
  files: 3
---

# Quick Task 260531-g5q: Group Binary Sensors Summary

**One-liner:** Replaced per-endpoint conditions sensor with one group binary sensor per Gatus group (ON=all-up, OFF=any-down) with green/red endpoint attributes.

## What Was Built

- **sensor.py**: Removed `GatusConditionsSensor` class and `SENSOR_TYPE_CONDITIONS` constant. `_SENSOR_TYPES` now contains only `response_time` and `uptime`. Setup no longer creates conditions entities.
- **binary_sensor.py**: Added `GatusGroupBinarySensor` class extending `CoordinatorEntity` + `BinarySensorEntity` directly. Setup creates one group entity per unique `ep["group"]` value. Stale cleanup updated to handle `_{SENSOR_TYPE}` and `_{GROUP_SENSOR_TYPE}` uid patterns.
- **tests/test_entities.py**: Removed conditions tests (Test 6, 6b) and `ENDPOINT_A_WITH_CONDITIONS` fixture. Added `TWO_GROUP_RESPONSE` fixture. Added 4 new tests: all-up, any-down, multiple groups, and no-conditions-sensor guard.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1    | 6a02006 | feat: remove conditions sensor; add GatusGroupBinarySensor |
| 2    | 23cf3b5 | test: remove conditions tests; add group sensor tests |

## Test Results

50/50 tests pass (full suite).

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED

- `custom_components/gatus/binary_sensor.py` — GatusGroupBinarySensor present ✓
- `custom_components/gatus/sensor.py` — GatusConditionsSensor absent ✓
- `tests/test_entities.py` — 10 entity tests, all pass ✓
- Commits 6a02006 and 23cf3b5 exist in git log ✓
