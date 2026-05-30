# Phase 2: Config Flow - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-31
**Phase:** 02-config-flow
**Areas discussed:** URL Validation, Config Entry Title, entity_id Prefix Mutability, Reauth Flow, Reconfigure Flow, Options Flow

---

## URL Validation

| Option | Description | Selected |
|--------|-------------|----------|
| Try the actual API endpoint | Hit GET /api/v1/endpoints/statuses with URL + API key; 2xx = valid, 401/403 = invalid_auth, connection error = cannot_connect | ✓ |
| HTTP connectivity check only | Any HTTP response = reachable; 401 would count as valid | |
| No validation — defer to coordinator | Accept syntactically valid URL, let first refresh surface errors | |

**User's choice:** Try the actual API endpoint
**Notes:** Follow-up — 401/403 should reject with `invalid_auth` error (not accept with warning). Same validation logic reused in Reconfigure Flow.

---

## Config Entry Title

| Option | Description | Selected |
|--------|-------------|----------|
| Hostname from URL | Extract hostname (e.g. status.example.com) | ✓ |
| Full URL | Show URL as entered | |
| User-supplied name field | Add a Name field to Config Flow | |

**User's choice:** Hostname from URL

---

## entity_id Prefix Mutability

| Option | Description | Selected |
|--------|-------------|----------|
| Set-once in entry.data | Stored in data; changing requires remove+re-add | ✓ |
| Changeable via Options Flow | Stored in options; changing renames all entities | |

**User's choice:** Set-once in entry.data

---

## Reauth Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Implement proper reauth in Phase 2 | async_step_reauth shows API key input; validates before saving | ✓ |
| Defer reauth to a later phase | Leave Phase 1 stub (aborts); user must remove+re-add | |

**User's choice:** Implement proper reauth in Phase 2

---

## Reconfigure Flow ("Allow Reload")

| Option | Description | Selected |
|--------|-------------|----------|
| Full reconfigure flow (URL + API key) | async_step_reconfigure; validates new values before saving | ✓ |
| Options Flow only — no reconfigure | URL/API key require remove+re-add | |
| Best-effort | Implement if straightforward | |

**User's choice:** Full reconfigure flow (URL + API key)
**Notes:** Validation for reconfigure should use the same logic as Config Flow.

---

## Options Flow

| Option | Description | Selected |
|--------|-------------|----------|
| Scan interval only | Only exposes scan_interval (30–300 s) | |
| Scan interval + API key | Exposes both; API key rotation without needing reauth or reconfigure | ✓ |

**User's choice:** Scan interval + API key
**Notes:** Pre-fill with current values. No re-validation of API key on Options Flow save — let coordinator surface auth errors.

---

## Agent's Discretion

- Form field types (selector vs plain voluptuous schema)
- Whether to use shared `_validate_input` helper or inline validation
- Prefix field — `vol.Optional` with default vs `vol.Required` with default

## Deferred Ideas

None.
