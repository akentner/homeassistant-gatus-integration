# Phase 2: Config Flow - Context

**Gathered:** 2026-05-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Config Flow (UI setup), Options Flow (scan interval + API key), Reauth Flow (fix bad/rotated key), and Reconfigure Flow (change URL + API key in-place). No entities. Goal: a user can add, configure, and reconfigure a Gatus instance entirely through the HA UI.

Requirements in scope: SETUP-01, SETUP-02, SETUP-03, SETUP-04, SETUP-05, SETUP-06

</domain>

<decisions>
## Implementation Decisions

### URL Validation (SETUP-03)
- **D-01:** Validation calls `GET /api/v1/endpoints/statuses` with the provided URL and API key (if any). A 2xx response (even empty array) is "valid". A connection error → `cannot_connect` error. A 401/403 → `invalid_auth` error. Do NOT accept the entry on auth failure.
- **D-02:** Same validation logic reused in both Config Flow and Reconfigure Flow (DRY — extract to a shared helper).

### Config Entry Data Shape
- **D-03:** `entry.data` stores: `url` (str), `api_key` (str | None), `prefix` (str, default `"gatus_"`). These are set-once at Config Flow; URL and API key can be changed via Reconfigure but go through re-validation.
- **D-04:** `entry.options` stores: `scan_interval` (int, 30–300, default 60), `api_key` (str | None). API key in options allows rotation via Options Flow without reconfigure. On coordinator setup, prefer `entry.options["api_key"]` over `entry.data["api_key"]` if options key is present.
- **D-05:** entity_id prefix is stored in `entry.data` only (set-once). Changing prefix requires remove + re-add. This prevents silent entity renames that break automations.

### Config Entry Title
- **D-06:** Title is the hostname extracted from the URL (e.g., `status.example.com`). Use `yarl.URL(url).host` or `urllib.parse.urlparse(url).hostname`. No user-supplied name field.

### Duplicate URL Detection (SETUP-04)
- **D-07:** Normalize URL before duplicate check: strip trailing slash, lowercase scheme and host. Compare normalized URL against all existing config entries for the same domain. Return `already_configured` abort if duplicate found.

### Reauth Flow
- **D-08:** Implement `async_step_reauth` in Phase 2. When coordinator raises `ConfigEntryAuthFailed`, HA triggers reauth. The reauth step presents an API key input (pre-filled empty). On success, update `entry.data["api_key"]` and reload the entry. Validate the new key via the same validation helper (D-01/D-02).

### Reconfigure Flow
- **D-09:** Implement `async_step_reconfigure`. Accessible via the integration's "..." menu. Allows changing URL and API key. Pre-fill current values. Validate new URL + key before saving. On success, update `entry.data` and trigger `async_schedule_config_entry_for_reload`.
- **D-10:** entity_id prefix is NOT editable via Reconfigure (set-once per D-05).

### Options Flow
- **D-11:** Options Flow exposes two fields: `scan_interval` (int slider/input, 30–300 s) and `api_key` (str, optional). Both pre-filled with current values.
- **D-12:** On Options Flow save, do NOT re-validate the API key — user may be clearing it or setting a placeholder; let the coordinator surface auth errors on next refresh.
- **D-13:** After Options Flow save, call `coordinator.update_interval = timedelta(seconds=new_scan_interval)` and trigger an immediate refresh.

### Agent's Discretion
- Form field types (selector.TextSelector vs plain str schema) — pick what's cleanest with HA voluptuous + selector patterns.
- Whether to use a single `_validate_input` helper or inline validation — pick the cleaner HA pattern.
- Whether prefix field uses a default value via `vol.Optional` or `vol.Required` with a default.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Requirements
- `.planning/REQUIREMENTS.md` — Full requirement list; Phase 2 scope: SETUP-01..SETUP-06
- `.planning/ROADMAP.md` §Phase 2 — Success criteria and dependency order
- `.planning/PROJECT.md` §Key Decisions — Locked architectural decisions

### HA Integration Conventions (from CLAUDE.md)
- `CLAUDE.md` §Architecture Libraries — Import paths for ConfigFlow, OptionsFlow, ConfigEntryAuthFailed, selector
- `CLAUDE.md` §What NOT to Use — Banned patterns
- `CLAUDE.md` §HA Integration Conventions — async_step_user, ConfigEntryNotReady, unique IDs

### Existing Phase 1 Code
- `custom_components/gatus/__init__.py` — Reads `entry.data["url"]`, `entry.data.get("api_key")`, `entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)`. Phase 2 must produce this exact shape.
- `custom_components/gatus/config_flow.py` — Phase 1 stub; Phase 2 replaces body entirely.
- `custom_components/gatus/const.py` — `DOMAIN`, `DEFAULT_SCAN_INTERVAL`; Phase 2 may add new constants.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `GatusDataUpdateCoordinator` in `coordinator.py` — Phase 2 validation helper can instantiate a temporary session (or use `async_get_clientsession`) to hit the API. Do not reuse the coordinator class for validation — keep it lightweight.
- `DEFAULT_SCAN_INTERVAL = 60` in `const.py` — use as default for Options Flow pre-fill.

### Established Patterns
- `entry.runtime_data` stores the coordinator (set in `__init__.py`). Phase 2 does not change this.
- `entry.data` vs `entry.options` split is already implied by `__init__.py`: URL/api_key/prefix → data; scan_interval → options (plus api_key added in Phase 2).

### Integration Points
- Config Flow output (`entry.data` + `entry.options`) is the contract consumed by `__init__.py`. Phase 2 must match the keys `__init__.py` already reads.
- Phase 3 will also read `entry.data["prefix"]` to build entity object IDs — establish the key name here.

</code_context>

<specifics>
## Specific Ideas

- Validation helper signature: `async _validate_gatus_connection(session, url, api_key) -> None` — raises `CannotConnect` or `InvalidAuth` (custom exceptions) for clean error mapping in flow steps.
- D-04 note: `coordinator.py` currently reads `api_key` only from `entry.data`. Phase 2 needs to update `__init__.py` to prefer `entry.options.get("api_key", entry.data.get("api_key"))` so Options Flow API key changes take effect on reload.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 02-config-flow*
*Context gathered: 2026-05-31*
