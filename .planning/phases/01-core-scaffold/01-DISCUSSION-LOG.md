# Phase 1: Core Scaffold - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 1-Core Scaffold
**Areas discussed:** coordinator.data Shape, HTTP Fehler-Taxonomie, Test-Scope Phase 1, manifest.json Strategie

---

## coordinator.data Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Dict[str, EndpointData] (TypedDict/dataclass) | Typed contract for Phase 3 entities | ✓ (Claude decides exact type) |
| Dict[str, dict] (raw) | Direct Gatus API response, no abstraction | |
| Du entscheidest | Claude picks best HA pattern | |

**User's choice:** Du entscheidest (coordinator data type) + endpoint_key as dict key

**Key follow-up:** endpoint_key (raw from Gatus API) as dict key — confirmed. Missing endpoints → key removed from data (enables Phase 3 reconciliation).

---

## HTTP Fehler-Taxonomie

| Option | Description | Selected |
|--------|-------------|----------|
| ConfigEntryAuthFailed | 401/403 → triggers HA re-auth flow | ✓ |
| ConfigEntryNotReady | Treats auth errors like connection errors | |
| Log + return empty dict | No exception, integration stays loaded | |

**401/403:** ConfigEntryAuthFailed ✓

| Option | Description | Selected |
|--------|-------------|----------|
| UpdateFailed (subsequent), ConfigEntryNotReady (first) | Standard HA coordinator pattern | ✓ |
| ConfigEntryNotReady always | Every error = retry from scratch | |

**Timeout/connection errors:** UpdateFailed (subsequent refreshes), ConfigEntryNotReady (first refresh only) ✓

**HTTP 200 + invalid JSON:** UpdateFailed with logged error message ✓

---

## Test-Scope Phase 1

| Option | Description | Selected |
|--------|-------------|----------|
| Coordinator + __init__.py | Full Phase 1 coverage | ✓ |
| Nur Coordinator | Minimal scope | |

**Mandatory test cases (all selected):**
1. Successful fetch → correct `coordinator.data` shape
2. First-refresh network failure → ConfigEntryNotReady
3. 401/403 → ConfigEntryAuthFailed
4. Setup/unload clean — no stale entry.runtime_data

---

## manifest.json Strategie

| Option | Description | Selected |
|--------|-------------|----------|
| Jetzt vollständig | All hassfest fields in Phase 1 | ✓ |
| Minimal jetzt, Rest Phase 4 | Risk of late surprises | |

**Codeowner:** @akentner ✓
**Startversion:** 0.1.0 ✓

---

## Claude's Discretion

- Internal data structure type for coordinator.data values (TypedDict vs dataclass) — Claude picks best HA convention.

## Deferred Ideas

None — discussion stayed within Phase 1 scope.
