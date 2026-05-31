---
phase: 03-entity-platforms
plan: "01"
subsystem: coordinator, entity-base
tags: [coordinator, entity, TypedDict, base-class, TDD]
dependency_graph:
  requires: [02-config-flow]
  provides: [GatusEndpoint-extended, GatusEntity-base]
  affects: [03-02-binary-sensor, 03-02-sensor]
tech_stack:
  added: []
  patterns: [CoordinatorEntity, DeviceInfo, TypedDict-extension, TDD-red-green]
key_files:
  modified:
    - custom_components/gatus/coordinator.py
    - tests/test_coordinator.py
  created:
    - custom_components/gatus/entity.py
key_decisions:
  - "consecutive_failures scans results newest-first (index 0 = latest); matches Gatus API order"
  - "uptime_pct is None (not 0.0) when results empty — explicit null sentinel for UI distinction"
  - "GatusEntity accepts platform_domain string to set entity_id prefix correctly for both binary_sensor and sensor"
metrics:
  duration_minutes: 4
  completed_date: "2026-05-31"
  tasks_completed: 2
  files_changed: 3
---

# Phase 03 Plan 01: Coordinator Data Contract Extension + Shared Entity Base

**One-liner:** Extended GatusEndpoint TypedDict with consecutive_failures/uptime_pct and created CoordinatorEntity-based GatusEntity base class.

## Objective

Extend the coordinator data contract and create the shared entity base class that all four entity types will inherit from. Plans 02 depends on these contracts being stable — changes here touch every entity type.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Extend GatusEndpoint + _parse_endpoint + tests | 9058afb | coordinator.py, test_coordinator.py |
| 2 | Create entity.py shared base class | b6ca83c | entity.py |

## What Was Built

### Task 1: GatusEndpoint TypedDict Extension (TDD)

Added two computed fields to `GatusEndpoint`:
- `consecutive_failures: int` — count of leading failed results scanning newest-first
- `uptime_pct: float | None` — `success_count / len(results) * 100`; `None` when results is empty

`_parse_endpoint` now computes both from the full `results[]` array (not just `results[0]`).

Added 5 new TDD tests covering all behavior spec cases:
- `[fail, fail, pass]` → consecutive_failures=2, uptime≈33.3%
- `[pass, fail]` → consecutive_failures=0, uptime=50.0%
- `[]` → consecutive_failures=0, uptime_pct=None
- all-pass → uptime=100.0%, consecutive_failures=0
- all-fail → uptime=0.0%, consecutive_failures=3
- 2-pass/2-fail → uptime=50.0%

Total coordinator tests: **14 passed**.

### Task 2: GatusEntity Base Class

Created `custom_components/gatus/entity.py` with `GatusEntity(CoordinatorEntity[GatusDataUpdateCoordinator])`:

- `_attr_has_entity_name = True` — defers display naming to subclasses
- `_attr_unique_id = f"{entry_id}_{endpoint_key}_{sensor_type}"` (DEVICE-02)
- `entity_id = f"{platform_domain}.{prefix}{endpoint_key}_{sensor_type}"` (DEVICE-03)
- `_attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"{entry_id}_{group}")}, name=group, manufacturer="Gatus")` (DEVICE-01)
- `available` property: guards on `super().available`, `coordinator.data is not None`, and key presence
- `_endpoint` property: convenience accessor for `coordinator.data[endpoint_key]`

## Verification

- `pytest tests/test_coordinator.py -v` → 14 passed ✓
- `ruff check coordinator.py entity.py` → no lint errors ✓
- `python -c "from custom_components.gatus.entity import GatusEntity; print('OK')"` → OK ✓

## Deviations from Plan

None - plan executed exactly as written.

## Self-Check: PASSED

- [x] `custom_components/gatus/coordinator.py` — exists, has `consecutive_failures` and `uptime_pct`
- [x] `custom_components/gatus/entity.py` — exists, exports `GatusEntity`
- [x] `tests/test_coordinator.py` — exists, 14 tests pass
- [x] Commit 9058afb — exists (Task 1)
- [x] Commit b6ca83c — exists (Task 2)
