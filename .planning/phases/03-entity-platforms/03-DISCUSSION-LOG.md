# Phase 3: Entity Platforms - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 03-entity-platforms
**Areas discussed:** Consecutive failures calc, Uptime % data source, Conditions sensor attributes, Stale entity cleanup strategy, Platform file structure

---

## Consecutive Failures Calc

| Option | Description | Selected |
|--------|-------------|----------|
| Count from results[] leading failures | Scan results[] in order; count leading failure entries until first success. No extra API calls. | ✓ |
| Re-fetch per-endpoint history | Call single-endpoint API for deeper history. Breaks coordinator single-fetch model. | |
| Best-effort from results[], cap at array length | Same as first option but explicitly acknowledged as capped at ~20. | |

**User's choice:** Count from results[] leading failures
**Notes:** Straightforward, no extra API calls, matches what Gatus UI shows.

---

## Uptime % Data Source

| Option | Description | Selected |
|--------|-------------|----------|
| Compute from results[] in coordinator | success_count / len(results) * 100. No API changes. | ✓ |
| Add ?duration param, verify first | Requires live Gatus verification. True 7-day window if supported. | |
| Defer uptime % to later phase | Skip SENS-07 now, add later after API verification. | |

**User's choice:** Compute from results[] in coordinator
**Notes:** Resolves the open concern from STATE.md in favour of simplicity.

---

## Conditions Sensor Attributes

| Option | Description | Selected |
|--------|-------------|----------|
| State only — X/Y string, no per-condition attrs | Minimal, clean. v2 requirements defer breakdown. | |
| X/Y state + condition_details attribute list | Full breakdown as [{condition, success}, ...] from conditionResults[]. | ✓ |
| X/Y state + first failing condition only | Just the failed_condition text as a single attribute. | |

**User's choice:** X/Y state + condition_details attribute list
**Notes:** Data is already in coordinator.data — no extra cost to expose it.

---

## Stale Entity Cleanup Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Remove in coordinator update callback | Compare coordinator.data keys to registry on each refresh. Remove immediately. | ✓ |
| Reconcile only at platform setup | Stale entities persist until HA restart. Violates DEVICE-04. | |
| Remove after N consecutive misses | Grace period for transient blips. Adds complexity. | |

**User's choice:** Remove in coordinator update callback
**Notes:** Immediate removal; transient blips cause UpdateFailed (unavailable state), not empty dict.

---

## Platform File Structure

| Option | Description | Selected |
|--------|-------------|----------|
| binary_sensor.py + sensor.py + shared base | Clean HA platform separation with reusable base. | ✓ |
| All entities in sensor.py, proxy binary_sensor.py | Simpler but requires proxy import for HA platform loader. | |
| Shared entities.py imported by both platforms | Maximum reuse, 3 files total, slight overkill for 4 classes. | |

**User's choice:** binary_sensor.py + sensor.py + shared base
**Notes:** Matches HA platform conventions exactly.

---

## Agent's Discretion

- Exact name of shared base file (entity.py, base.py, or inline)
- Whether error_reason uses helper function or inline extraction
- Whether uptime % is rounded or raw float

## Deferred Ideas

- Summary/aggregate sensor: % of green endpoints + healthy/unhealthy endpoint lists as attributes. Suggested by user — new capability beyond REQUIREMENTS.md scope.
