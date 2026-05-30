---
phase: 02-config-flow
plan: "02"
subsystem: config-flow
tags: [config-flow, tdd, options-flow, reauth, reconfigure]
dependency_graph:
  requires: [02-01-config-flow-user-step]
  provides: [OptionsFlowHandler, GatusConfigFlow.async_step_reauth, GatusConfigFlow.async_step_reconfigure]
  affects: [__init__.py-api-key-preference]
tech_stack:
  added: []
  patterns: [tdd-red-green, options-flow, reauth-flow, reconfigure-flow, NumberSelectorMode-type-safety]
key_files:
  created: []
  modified:
    - custom_components/gatus/config_flow.py
    - custom_components/gatus/__init__.py
    - custom_components/gatus/strings.json
    - custom_components/gatus/translations/en.json
    - tests/test_config_flow.py
decisions:
  - "NumberSelector without min/max bounds in options schema — selector min/max causes HA to raise InvalidData before handler code runs; bounds validated in handler instead"
  - "NumberSelectorMode.BOX enum used (not string 'box') for mypy type safety"
  - "OptionsFlow initialized without config_entry argument — modern HA 2024+ pattern uses self.config_entry property automatically"
metrics:
  duration: "~20 minutes"
  completed: "2026-05-31"
  tasks: 2
  files: 5
---

# Phase 02 Plan 02: Options/Reauth/Reconfigure Flows Summary

**One-liner:** Complete config flow with live scan-interval tuning, API key rotation via options, reauth on 401, and in-place URL reconfiguration — all TDD-verified with 13 new tests.

## What Was Built

Extended the Gatus Config Flow with three additional flows:

1. **OptionsFlowHandler** — scan interval (30–300 s) and API key rotation post-setup. Updates `coordinator.update_interval` live (no reload needed for interval changes).
2. **async_step_reauth / async_step_reauth_confirm** — re-authentication flow triggered by HA when coordinator raises `ConfigEntryAuthFailed`. Validates new key via shared `_validate_gatus_connection` helper.
3. **async_step_reconfigure** — in-place URL and API key update. Validates new URL, updates unique_id, calls `async_update_reload_and_abort`. Preserves `prefix` from original setup (not exposed for change per D-10).

Also fixed `__init__.py` to prefer `entry.options["api_key"]` over `entry.data["api_key"]`, ensuring API key set via Options Flow takes effect on next reload.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Options/Reauth/Reconfigure flows (TDD) | 184f648 | config_flow.py, test_config_flow.py |
| 2 | Fix __init__.py api_key preference + strings | 90af413 | __init__.py, strings.json, translations/en.json |

## Decisions Made

1. **NumberSelector without min/max** in options schema — HA validates `NumberSelectorConfig(min=..., max=...)` server-side, raising `InvalidData` before handler code runs. Bounds validated in handler code instead (`errors["scan_interval"] = "scan_interval_out_of_range"`).
2. **`NumberSelectorMode.BOX` enum** (not string `"box"`) for mypy `TypedDict` type safety.
3. **OptionsFlow without config_entry constructor arg** — modern HA 2024+ pattern; `self.config_entry` is set by framework automatically.
4. **`_get_reauth_entry()` / `_get_reconfigure_entry()`** — HA 2024+ helpers used for clean entry access in reauth/reconfigure flows.
5. **Options data shape** — `{"scan_interval": int, "api_key": str | None}` — api_key None when cleared (empty string normalized).

## Test Coverage

20 tests total (7 from Plan 01 + 13 new):
- OPT-1: Options form shows with current values pre-filled
- OPT-2: scan_interval=120 → coordinator.update_interval updated live
- OPT-3: api_key rotation stored in options
- OPT-4: empty api_key → None in options
- OPT-5: out-of-range scan_interval → form error
- REAUTH-1: reauth trigger → form shown
- REAUTH-2: valid key → entry updated, reload, abort reauth_successful
- REAUTH-3: invalid key → form re-shown with invalid_auth error
- RECONF-1: reconfigure shows form with current values pre-filled
- RECONF-2: valid new URL → entry updated, abort reconfigure_successful
- RECONF-3: unreachable URL → form re-shown with cannot_connect error
- RECONF-4: prefix not exposed in reconfigure form; preserved in entry.data
- COEX-1: two entries with different URLs coexist without conflict

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] NumberSelector min/max causes InvalidData, not form errors**
- **Found during:** Task 1 GREEN phase
- **Issue:** `NumberSelectorConfig(min=30, max=300)` causes HA to raise `homeassistant.data_entry_flow.InvalidData` when test sends out-of-bounds values, instead of returning FORM with errors
- **Fix:** Removed min/max from `NumberSelectorConfig`; kept handler-level bounds validation returning `errors["scan_interval"] = "scan_interval_out_of_range"`
- **Files modified:** `config_flow.py`
- **Commit:** 184f648

## Self-Check: PASSED
