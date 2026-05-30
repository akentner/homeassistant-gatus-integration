# Research Summary: homeassistant-gatus-integration

**Synthesized:** 2026-05-30
**Sources:** STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md, PROJECT.md

---

## Executive Summary

Greenfield HA custom integration polling the Gatus uptime monitoring API. Domain well-understood: HA has a canonical pattern for polling REST integrations (DataUpdateCoordinator + CoordinatorEntity + Config Flow) that is thoroughly documented and enforced by hassfest and HACS validators. No architectural invention required — correct application of established patterns is the entire job.

Coordinator pattern must be correct from the start — every entity depends on it and retrofitting touches the entire codebase. No third-party pip dependencies; all HTTP infrastructure comes from HA's shared aiohttp session.

Primary risks are mechanical, not algorithmic: deprecated APIs, missing cleanup in `async_unload_entry`, and a Gatus-specific data quirk (durations are nanoseconds, not milliseconds).

---

## Stack

| Technology | Version | Role |
|------------|---------|------|
| Python | 3.14+ | Runtime (HA 2026.7 requirement) |
| homeassistant | 2026.3.2 (dev pin) | Framework — do NOT pin in manifest |
| aiohttp | 3.13.5 (via HA) | HTTP — use `async_get_clientsession(hass)` exclusively |
| ruff | 0.15.7 | Lint + format |
| pytest-homeassistant-custom-component | 0.13.334 | HA test fixtures |

No third-party pip dependencies. `requirements: []` in manifest.json.

---

## Table Stakes (v1 must-haves)

1. Config Flow with URL + optional API key, URL reachability validation, duplicate detection
2. DataUpdateCoordinator with `async_config_entry_first_refresh` and `ConfigEntryNotReady`
3. Binary sensor per endpoint (connectivity class, on=up, off=down) with attributes: `last_check_timestamp`, `error_reason`, `response_duration_ms`, `consecutive_failures`
4. Response time sensor per endpoint (device_class: duration, unit: milliseconds)
5. Uptime % sensor per endpoint (7-day window, float)
6. Options Flow for scan interval (30–300 s)
7. Device grouping by Gatus group name, scoped by `entry_id`
8. Unique entity IDs: `{entry_id}_{endpoint_key}_{sensor_type}`
9. HACS-ready `hacs.json` + `manifest.json`
10. English strings/translations

---

## Architecture

**Data flow:** Coordinator fetches `GET /api/v1/endpoints/statuses` once per interval → `coordinator.data = {endpoint_key: endpoint_dict}` → all entities notified via callback → each entity reads its key, sets `_attr_*`, calls `async_write_ha_state()`.

**Key pattern:** All entity classes inherit `CoordinatorEntity[GatusDataUpdateCoordinator]` alongside platform base → `should_poll = False`, automatic update subscription, availability tracking.

**Use `entry.runtime_data`** (not deprecated `hass.data[DOMAIN]`) with `type GatusConfigEntry = ConfigEntry[GatusDataUpdateCoordinator]` alias.

---

## Build Order

Dependencies flow strictly downward:

```
1. const.py
2. manifest.json
3. strings.json + translations/en.json   ← create BEFORE config_flow.py
4. coordinator.py
5. config_flow.py
6. __init__.py
7. binary_sensor.py
8. sensor.py
9. hacs.json
```

---

## Top 5 Critical Pitfalls

1. **Own aiohttp session (P1):** Never `aiohttp.ClientSession()`. Always `async_get_clientsession(hass)`.
2. **Missing `async_unload_entry` cleanup (P7):** `async_unload_platforms` + pop `entry.entry_id`. Without this, reloads leave duplicate coordinators.
3. **`async_config_entry_first_refresh` not called (P8):** Must await this before platform setup. Skipping → `coordinator.data = None` → crashes.
4. **Gatus durations are nanoseconds (P14):** `42000000` = 42 ms. Divide by `1_000_000`.
5. **Deprecated singular setup (P6):** `async_forward_entry_setups` (plural, list), not singular.

---

## Suggested Phase Structure

| Phase | Focus | Key Pitfalls |
|-------|-------|-------------|
| 1 — Core Scaffold | coordinator + `__init__.py` | P1, P4, P6, P7, P8 |
| 2 — Config Flow | config_flow.py, strings | P5, P11, P12 |
| 3 — Entity Platforms | binary_sensor.py, sensor.py | P2, P3, P14, P15, P16 |
| 4 — HACS + CI | hacs.json, GitHub Actions | P9, P10 |
| 5 — Differentiators | conditions sensor, diagnostics | post-MVP |

---

## Open Questions

1. **Entity removal (P3):** Accept stale unavailable entities (simpler) or implement active reconciliation via `entity_registry.async_remove`? Decision needed before Phase 3.
2. **Configurable entity_id prefix:** `PROJECT.md` lists this as Active requirement — clarify whether it is a Config Flow field or derived automatically from DOMAIN.
3. **Uptime % data source:** `/api/v1/endpoints/statuses` returns last N results (default 20). True 7-day uptime may require `?duration=604800000000000` query param. Verify against live Gatus instance.

---

## Confidence

| Area | Confidence |
|------|------------|
| Stack | HIGH |
| Features / table stakes | HIGH |
| Architecture | HIGH |
| Pitfalls | HIGH |
| Gatus API shape | MEDIUM (not verified against live instance) |
