# Phase 1: Core Scaffold - Research

**Researched:** 2026-05-31
**Domain:** Home Assistant DataUpdateCoordinator, config entry lifecycle, aiohttp session management
**Confidence:** HIGH

## Summary

Phase 1 builds the data-pipeline skeleton for the Gatus HA integration: a `DataUpdateCoordinator` subclass that polls `GET /api/v1/endpoints/statuses`, stores endpoint data keyed by `endpoint_key`, handles HTTP errors correctly, and wires into the HA config entry lifecycle via `async_setup_entry` / `async_unload_entry`. No sensor entities are created in this phase — Phase 3 consumes `coordinator.data`.

The standard HA coordinator pattern is well-documented and matches every locked decision in CONTEXT.md. The critical mechanism to get right is `async_config_entry_first_refresh()`: it automatically converts `UpdateFailed` into `ConfigEntryNotReady` on the first refresh, so `_async_update_data` must raise only `UpdateFailed` and `ConfigEntryAuthFailed` — never `ConfigEntryNotReady` directly. Getting this wrong (raising `ConfigEntryNotReady` from `_async_update_data`) will suppress auth-error detection on first run.

One explicit sequencing gap from CONTEXT.md must be flagged: D-09 sets `config_flow: true` in the manifest, but `config_flow.py` does not exist until Phase 2. This is fine for tests (which use `MockConfigEntry`, bypassing the flow) and acceptable because hassfest validation is deferred to Phase 4, but the plan must acknowledge the integration cannot be added via the HA UI until Phase 2.

**Primary recommendation:** Implement `GatusDataUpdateCoordinator` as a thin `DataUpdateCoordinator[dict[str, GatusEndpoint]]` subclass holding session/URL/API-key directly (not via `runtime_data.client`) to avoid the runtime_data ordering trap with `async_config_entry_first_refresh`.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**D-01:** `coordinator.data` is a `Dict[str, <typed structure>]` keyed by `endpoint_key` (raw from Gatus API, e.g. `core_my-service`). Claude chooses the best typed structure (TypedDict or dataclass) per HA conventions.

**D-02:** When an endpoint disappears from the API response, its key is removed from `coordinator.data`. This enables Phase 3 active reconciliation (DEVICE-04).

**D-03:** HTTP 401/403 → raise `ConfigEntryAuthFailed`. Triggers HA re-auth flow. Correct signal for bad API key.

**D-04:** Network errors (timeout, connection refused) and non-auth HTTP errors → raise `UpdateFailed` (for subsequent refreshes). Only on the FIRST refresh does a network error become `ConfigEntryNotReady` — this conversion is done automatically by `async_config_entry_first_refresh()`, not by the coordinator itself.

**D-05:** HTTP 200 with invalid/unparseable JSON → raise `UpdateFailed` with error message logged. Do not silently return empty dict.

**D-06:** Test both Coordinator and `__init__.py` (setup/unload) in Phase 1.

**D-07:** Mandatory test cases:
1. Successful fetch — `coordinator.data` has correct shape keyed by `endpoint_key`
2. First-refresh network failure → `ConfigEntryNotReady` raised
3. 401/403 response → `ConfigEntryAuthFailed` raised
4. Integration setup and unload are clean — no stale `entry.runtime_data`

**D-08:** Finalize manifest.json completely in Phase 1 (all hassfest-required fields). Phase 4 validates, does not change.

**D-09:** Fields: `domain: gatus`, `name: Gatus`, `codeowners: ["@akentner"]`, `config_flow: true`, `integration_type: hub`, `iot_class: cloud_polling`, `version: "0.1.0"`, `requirements: []`.
**RESEARCH NOTE:** D-09's field list is incomplete. `documentation` is listed as a required manifest field by the official HA docs and hassfest will warn/fail without it. `issue_tracker` is strongly recommended (present in the ludeeus blueprint). The plan must add `documentation` (and optionally `issue_tracker`) beyond D-09's list. See Pitfall 1 below.

### Claude's Discretion

- Internal data structure type (TypedDict vs dataclass) — Claude picks best HA pattern.

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.

</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| POLL-01 | Integration polls `GET /api/v1/endpoints/statuses` via shared aiohttp session | `async_get_clientsession(hass)` + coordinator `_async_update_data`; see Code Examples §Fetch Pattern |
| POLL-02 | API key sent as `Authorization: Bearer <token>` when provided | Conditional header injection in `_async_update_data`; never log the token (V2/security) |
| POLL-03 | Coordinator raises `ConfigEntryNotReady` if first refresh fails | `async_config_entry_first_refresh()` auto-converts `UpdateFailed` → `ConfigEntryNotReady`; D-04 mechanism |
| POLL-04 | Default scan interval is 60 s | `update_interval=timedelta(seconds=60)` in `super().__init__()` |

</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| HTTP polling (Gatus API) | Coordinator (Python/HA) | — | All HTTP via `async_get_clientsession`; one call per interval |
| Error classification (auth vs network vs parse) | Coordinator `_async_update_data` | HA config entry machinery | Coordinator raises typed exceptions; HA machinery handles retry/reauth |
| First-refresh failure → `ConfigEntryNotReady` | HA (`async_config_entry_first_refresh`) | — | HA stdlib converts `UpdateFailed` to `ConfigEntryNotReady` automatically |
| Coordinator lifecycle (create/store/cleanup) | `__init__.py` `async_setup_entry` | `async_unload_entry` | Standard HA config entry pattern |
| Runtime data storage | `entry.runtime_data` | — | Typed; auto-cleaned on unload; replaces deprecated `hass.data[DOMAIN]` |
| Data shape (`coordinator.data`) | Coordinator | — | `dict[str, GatusEndpoint]` keyed by `endpoint_key` — contract for Phase 3 |

## Standard Stack

### Core (all from `homeassistant` package — no pip installs at runtime)

| Library | Import Path | Purpose | Why Standard |
|---------|-------------|---------|--------------|
| `DataUpdateCoordinator` | `homeassistant.helpers.update_coordinator` | Single polling point; entities subscribe | HA-required pattern for polling integrations |
| `UpdateFailed` | `homeassistant.helpers.update_coordinator` | Signals transient fetch failure | Enables coordinator retry scheduling |
| `ConfigEntryNotReady` | `homeassistant.exceptions` | Signals first-refresh failure to HA | HA retries setup automatically when raised from `async_setup_entry` |
| `ConfigEntryAuthFailed` | `homeassistant.exceptions` | Signals 401/403 → triggers reauth flow | Correct HA signal for bad credentials |
| `async_get_clientsession` | `homeassistant.helpers.aiohttp_client` | Shared aiohttp session | Never create standalone ClientSession |
| `ConfigEntry` | `homeassistant.config_entries` | Config entry base; generic `ConfigEntry[T]` | `type GatusConfigEntry = ConfigEntry[GatusCoordinator]` alias |

### Development / Testing

| Tool | Version (pinned in CLAUDE.md) | Latest on PyPI | Purpose |
|------|-------------------------------|----------------|---------|
| `pytest-homeassistant-custom-component` | 0.13.334 | 0.13.334 [VERIFIED: pypi.org] | HA fixtures: `hass`, `MockConfigEntry`, `aioclient_mock` |
| `pytest` | 9.0.3 | 9.0.3 [VERIFIED: pypi.org] | Test runner |
| `pytest-asyncio` | 1.4.0 (CLAUDE.md pin) | 1.1.0 [VERIFIED: pypi.org] | Async test support (`asyncio_mode = auto`) |
| `pytest-cov` | 7.1.0 | 7.1.0 [VERIFIED: pypi.org] | Coverage |
| `ruff` | 0.15.7 (CLAUDE.md pin) | 0.15.15 [VERIFIED: pypi.org] | Lint + format |
| `mypy` | 2.1.0 | 2.1.0 [VERIFIED: pypi.org] | Type checking |

**Version drift note:** `pytest-asyncio` CLAUDE.md pins 1.4.0 but PyPI latest is 1.1.0. This suggests CLAUDE.md's version is aspirational/future. Use whatever resolves cleanly against `pytest-homeassistant-custom-component`'s pinned transitive deps — do not manually override. `ruff` 0.15.7 vs 0.15.15: both are fine; 0.15.15 is safe to use.

**Installation (dev/test env only):**
```bash
uv add --dev pytest-homeassistant-custom-component pytest pytest-asyncio pytest-cov ruff mypy
```

## Package Legitimacy Audit

> slopcheck was unavailable on this machine. All packages below are tagged `[ASSUMED]`. The planner must gate each dev-dependency install behind a `checkpoint:human-verify` task.

| Package | Registry | Ecosystem | Source Repo | slopcheck | Disposition |
|---------|----------|-----------|-------------|-----------|-------------|
| `pytest-homeassistant-custom-component` | PyPI | Python | github.com/MatthewFlamm/pytest-homeassistant-custom-component | unavailable | [ASSUMED] — checkpoint required |
| `ruff` | PyPI | Python | github.com/astral-sh/ruff | unavailable | [ASSUMED] — checkpoint required |
| `pytest` | PyPI | Python | github.com/pytest-dev/pytest | unavailable | [ASSUMED] — checkpoint required |
| `pytest-asyncio` | PyPI | Python | github.com/pytest-dev/pytest-asyncio | unavailable | [ASSUMED] — checkpoint required |
| `pytest-cov` | PyPI | Python | github.com/pytest-dev/pytest-cov | unavailable | [ASSUMED] — checkpoint required |
| `mypy` | PyPI | Python | github.com/python/mypy | unavailable | [ASSUMED] — checkpoint required |

**Packages removed due to [SLOP]:** none
**Packages flagged [SUS]:** none — all are well-known ecosystem tools with documented source repos; manual verification expected to pass.

*All packages above are `[ASSUMED]` because slopcheck was unavailable. The planner must insert a `checkpoint:human-verify` before each install.*

## Architecture Patterns

### System Architecture Diagram

```
HA Startup
    │
    ▼
async_setup_entry(hass, entry)
    │
    ├─► Create GatusDataUpdateCoordinator(hass, url, api_key, scan_interval)
    │       │  (holds session ref, url, api_key — NOT via runtime_data.client)
    │       │
    ▼       ▼
coordinator.async_config_entry_first_refresh()
    │
    ├─► _async_update_data()
    │       │
    │       ├─► GET /api/v1/endpoints/statuses
    │       │       Authorization: Bearer <token>  (if api_key set)
    │       │
    │       ├─ 401/403 ─────────────────────────► raise ConfigEntryAuthFailed
    │       ├─ network error / non-auth HTTP error ► raise UpdateFailed
    │       ├─ 200 + invalid JSON ────────────────► raise UpdateFailed (logged)
    │       └─ 200 + valid JSON ──────────────────► return dict[endpoint_key, GatusEndpoint]
    │
    ├─ UpdateFailed on first refresh ──────► auto-converted to ConfigEntryNotReady
    │                                            (by async_config_entry_first_refresh)
    │                                            HA retries setup later
    │
    ├─ ConfigEntryAuthFailed ──────────────► HA triggers reauth flow
    │
    └─ Success: coordinator.data populated
    │
    ▼
entry.runtime_data = coordinator
    │
    ▼
return True  (no platform forwarding in Phase 1)

─────────── Scheduled polling ────────────────
HA timer fires every 60 s
    │
    ▼
coordinator._async_update_data()   (same logic as above)
    │
    └─ UpdateFailed here → coordinator.last_update_success = False
       ConfigEntryAuthFailed here → reauth flow triggered

─────────── Unload ───────────────────────────
async_unload_entry(hass, entry)
    │
    └─ entry.runtime_data cleared automatically by HA
       return True
```

### Recommended Project Structure

```
custom_components/gatus/
├── __init__.py          # async_setup_entry / async_unload_entry; no platforms in Phase 1
├── coordinator.py       # GatusDataUpdateCoordinator + GatusEndpoint TypedDict/dataclass
├── const.py             # DOMAIN, DEFAULT_SCAN_INTERVAL
└── manifest.json        # All required fields (see D-08/D-09 + documentation field)

tests/
├── conftest.py          # MockConfigEntry fixture; enable_custom_integrations
├── test_coordinator.py  # D-07 mandatory test cases
└── test_init.py         # setup/unload clean-state tests
```

### Pattern 1: Coordinator Subclass (no-platform Phase 1 variant)

```python
# Source: ludeeus/integration_blueprint coordinator.py + HA developers.home-assistant.io
# IMPORTANT: uses asyncio.timeout() (stdlib), NOT async_timeout (banned per CLAUDE.md)

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class GatusEndpoint(TypedDict):
    key: str
    name: str
    group: str
    success: bool
    duration_ms: int          # nanoseconds / 1_000_000
    timestamp: str            # ISO 8601
    condition_results: list   # raw from API


class GatusDataUpdateCoordinator(DataUpdateCoordinator[dict[str, GatusEndpoint]]):
    """Fetch Gatus endpoint data on a schedule."""

    def __init__(
        self,
        hass: HomeAssistant,
        url: str,
        api_key: str | None,
        scan_interval: int,
    ) -> None:
        self._url = url.rstrip("/")
        self._api_key = api_key  # NEVER log this value
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict[str, GatusEndpoint]:
        """Fetch all endpoint statuses from Gatus API."""
        session = async_get_clientsession(self.hass)
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        try:
            async with asyncio.timeout(10):
                resp = await session.get(
                    f"{self._url}/api/v1/endpoints/statuses",
                    headers=headers,
                )
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Gatus: {err}") from err

        if resp.status in (401, 403):
            raise ConfigEntryAuthFailed(
                f"Invalid API key (HTTP {resp.status})"
            )
        if resp.status != 200:
            raise UpdateFailed(f"Unexpected HTTP {resp.status} from Gatus")

        try:
            data = await resp.json()
        except Exception as err:
            raise UpdateFailed(f"Invalid JSON from Gatus: {err}") from err

        result: dict[str, GatusEndpoint] = {}
        for ep in data:
            key = ep["key"]
            latest = ep.get("results", [{}])[0]
            result[key] = GatusEndpoint(
                key=key,
                name=ep.get("name", key),
                group=ep.get("group", ""),
                success=latest.get("success", False),
                duration_ms=latest.get("duration", 0) // 1_000_000,
                timestamp=latest.get("timestamp", ""),
                condition_results=latest.get("conditionResults", []),
            )
        return result
```

### Pattern 2: async_setup_entry (Phase 1 — no platforms)

```python
# Source: developers.home-assistant.io/blog/2024/04/30/store-runtime-data-inside-config-entry/
# Phase 1 only: no async_forward_entry_setups — no entities yet

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DEFAULT_SCAN_INTERVAL
from .coordinator import GatusDataUpdateCoordinator

type GatusConfigEntry = ConfigEntry[GatusDataUpdateCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: GatusConfigEntry) -> bool:
    """Set up Gatus from a config entry."""
    coordinator = GatusDataUpdateCoordinator(
        hass,
        url=entry.data["url"],
        api_key=entry.data.get("api_key"),
        scan_interval=entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
    )
    # async_config_entry_first_refresh auto-converts UpdateFailed → ConfigEntryNotReady
    # ConfigEntryAuthFailed propagates as-is → HA triggers reauth
    # Do NOT raise ConfigEntryNotReady directly from _async_update_data
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    # Phase 1: no platforms; add PLATFORMS forwarding in Phase 3
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GatusConfigEntry) -> bool:
    """Unload a config entry."""
    # entry.runtime_data is cleared automatically; no platforms to unload in Phase 1
    return True
```

### Pattern 3: Test Structure

```python
# Source: MatthewFlamm/pytest-homeassistant-custom-component README
# conftest.py
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

# pytest.ini / pyproject.toml must have:
#   [tool.pytest.ini_options]
#   asyncio_mode = "auto"

# test_coordinator.py example
from unittest.mock import AsyncMock, patch

async def test_coordinator_successful_fetch(hass, aioclient_mock):
    """D-07 case 1: coordinator.data has correct shape keyed by endpoint_key."""
    aioclient_mock.get(
        "http://gatus.example.com/api/v1/endpoints/statuses",
        json=[{"key": "core_my-service", "name": "my-service", "group": "core",
               "results": [{"success": True, "duration": 42000000,
                            "conditionResults": [], "timestamp": "2024-01-01T00:00:00Z"}]}],
    )
    entry = MockConfigEntry(
        domain="gatus",
        data={"url": "http://gatus.example.com", "api_key": None},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = entry.runtime_data
    assert "core_my-service" in coordinator.data
    assert coordinator.data["core_my-service"]["success"] is True
    assert coordinator.data["core_my-service"]["duration_ms"] == 42  # 42000000 ns


async def test_first_refresh_failure_raises_not_ready(hass, aioclient_mock):
    """D-07 case 2: network failure on first refresh → ConfigEntryNotReady."""
    from homeassistant.exceptions import ConfigEntryNotReady
    aioclient_mock.get(
        "http://gatus.example.com/api/v1/endpoints/statuses",
        exc=Exception("connection refused"),
    )
    entry = MockConfigEntry(
        domain="gatus",
        data={"url": "http://gatus.example.com", "api_key": None},
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.async_setup(entry.entry_id)
    assert result is False  # entry not loaded

# test_scheduled_refetch.py — D-07 does not mandate this but success criterion 4 requires it
# Use: async_fire_time_changed(hass, utcnow() + timedelta(seconds=60))
# to advance HA's internal clock and trigger the coordinator's next scheduled poll.
```

### Anti-Patterns to Avoid

- **Raising `ConfigEntryNotReady` directly from `_async_update_data`:** This bypasses `async_config_entry_first_refresh`'s auto-conversion logic. Only `UpdateFailed` and `ConfigEntryAuthFailed` belong in `_async_update_data`.
- **Creating a standalone `aiohttp.ClientSession`:** Always use `async_get_clientsession(self.hass)`. Standalone sessions leak and are banned by HA conventions.
- **Using `async_timeout.timeout()`:** Banned per CLAUDE.md. Use `asyncio.timeout()` (Python 3.11+ stdlib).
- **Using `hass.data[DOMAIN][entry_id]`:** Deprecated since HA 2024+. Use `entry.runtime_data`.
- **Calling `async_forward_entry_setups` in Phase 1:** No platforms exist yet. Add this in Phase 3.
- **Logging the API key / Bearer token:** Security violation (ASVS V2). Log only a redacted form if needed (e.g., "API key configured: yes/no").
- **Assigning `entry.runtime_data` before `async_config_entry_first_refresh` when the coordinator reads from `runtime_data`:** If the coordinator's `_async_update_data` reads `self.config_entry.runtime_data.client`, `runtime_data` must be set before the first refresh. For Gatus, avoid this trap entirely by passing url/api_key directly into the coordinator constructor.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Coordinated polling across entities | Custom polling loop per entity | `DataUpdateCoordinator` | N entities × 1 HTTP call vs N entities × N calls; built-in retry, error tracking |
| First-refresh failure handling | Manual `try/except ConfigEntryNotReady` wrapper | `coordinator.async_config_entry_first_refresh()` | Auto-converts `UpdateFailed` → `ConfigEntryNotReady`; handles retry |
| Config entry state storage | `hass.data[DOMAIN][entry_id]` dict | `entry.runtime_data` (typed) | Type-safe, auto-cleaned on unload, no dict key collisions |
| Auth error signal | Custom exception or boolean | `ConfigEntryAuthFailed` | Triggers HA's built-in reauth flow automatically |
| HTTP session management | `aiohttp.ClientSession()` | `async_get_clientsession(hass)` | Shared, connection-pooled, lifecycle-managed by HA |

**Key insight:** The HA framework handles all the hard parts of a polling integration (retry scheduling, first-refresh semantics, reauth flows, entity state invalidation on failure). Don't duplicate any of this.

## Common Pitfalls

### Pitfall 1: Missing `documentation` field in manifest.json

**What goes wrong:** hassfest validation fails in Phase 4 with "required field 'documentation' missing". Integration loads with a warning in HA logs even before Phase 4.

**Why it happens:** D-09's decision list does not include `documentation`. The HA manifest spec ([CITED: developers.home-assistant.io/docs/creating_integration_manifest/]) lists it as required.

**How to avoid:** Add `"documentation": "https://github.com/akentner/homeassistant-gatus-integration"` (and optionally `"issue_tracker"`) to manifest.json in Phase 1. The plan must add these fields beyond D-09's list.

**Warning signs:** `hassfest` output, HA startup log "Integration gatus does not provide documentation".

### Pitfall 2: `config_flow: true` with no `config_flow.py` until Phase 2

**What goes wrong:** HA will fail to discover the config flow handler. The integration cannot be set up via UI in Phase 1. If hassfest runs against the Phase 1 repo state, it will warn about the missing module.

**Why it happens:** D-08/D-09 finalize the manifest in Phase 1, but Config Flow is Phase 2 work.

**How to avoid:** In Phase 1, either (a) add a minimal stub `config_flow.py` that raises `NotImplementedError`, or (b) document this known state in code comments. Tests use `MockConfigEntry` which bypasses the flow — this is fine for Phase 1. Hassfest validation is deferred to Phase 4.

**Warning signs:** HA log "No config flow found for domain gatus" when trying to add via UI.

### Pitfall 3: Raising ConfigEntryNotReady from `_async_update_data`

**What goes wrong:** Double-raise or masked `ConfigEntryAuthFailed`. If `_async_update_data` raises `ConfigEntryNotReady` directly, the auth-error signal from `ConfigEntryAuthFailed` is never surfaced — both network failures and auth failures look identical to HA.

**Why it happens:** POLL-03's wording ("coordinator raises ConfigEntryNotReady") is ambiguous about *who* raises it.

**How to avoid:** `_async_update_data` raises only `UpdateFailed` (network/parse/non-auth HTTP errors) and `ConfigEntryAuthFailed` (401/403). `async_config_entry_first_refresh()` converts `UpdateFailed` → `ConfigEntryNotReady` on the first call only. `ConfigEntryAuthFailed` propagates unchanged. [CITED: developers.home-assistant.io/docs/integration_fetching_data/]

**Warning signs:** Auth errors silently appear as "coordinator unavailable" rather than triggering reauth flow.

### Pitfall 4: `asyncio.timeout` import confusion

**What goes wrong:** Code uses `async with async_timeout.timeout(10):` (the banned form) instead of `asyncio.timeout()` (stdlib since Python 3.11).

**Why it happens:** HA's own developer documentation example (fetched from integration_fetching_data page) still shows the `async_timeout` import. Training data and docs are stale.

**How to avoid:** Use `async with asyncio.timeout(10):` — no separate import needed, it's part of `asyncio`. CLAUDE.md explicitly bans the `async_timeout` module.

**Warning signs:** `ruff` may catch this; `mypy` will type-check it; CLAUDE.md §What NOT to Use.

### Pitfall 5: Coordinator reads `runtime_data` before it's set

**What goes wrong:** `_async_update_data` calls `self.config_entry.runtime_data.client`, but `runtime_data` is set *after* `async_config_entry_first_refresh()` completes — so the first refresh reads `None.client` and raises `AttributeError`.

**Why it happens:** The ludeeus blueprint pattern stores `client` in `runtime_data`, then creates the coordinator with a reference back. If Phase 1 copies this without adjustment, the ordering is wrong.

**How to avoid:** Pass `url`, `api_key`, and other parameters directly into the coordinator's `__init__`. The coordinator does not need to read from `runtime_data`. Only after `async_config_entry_first_refresh()` succeeds should `entry.runtime_data = coordinator` be assigned.

**Warning signs:** `AttributeError: 'NoneType' object has no attribute 'client'` on first load.

### Pitfall 6: Scheduled re-fetch not tested

**What goes wrong:** Tests verify the first refresh but not the scheduler — coordinator silently stops polling after some edge case.

**Why it happens:** D-07's mandatory tests don't include the scheduling test, but success criterion 4 requires it.

**How to avoid:** Add one test using `async_fire_time_changed(hass, utcnow() + timedelta(seconds=60))` from `homeassistant.util.dt` to verify the coordinator re-fetches on schedule. This is not mandatory per D-07 but covers success criterion 4.

## Code Examples

### asyncio.timeout() — correct form (Python 3.11+ / HA pattern)

```python
# Source: Python 3.11+ stdlib; confirmed via CLAUDE.md §What NOT to Use
import asyncio

async with asyncio.timeout(10):
    resp = await session.get(url, headers=headers)
# NOT: async with async_timeout.timeout(10):  ← banned
```

### Type Alias for ConfigEntry

```python
# Source: developers.home-assistant.io/blog/2024/04/30/store-runtime-data-inside-config-entry/
from homeassistant.config_entries import ConfigEntry
from .coordinator import GatusDataUpdateCoordinator

type GatusConfigEntry = ConfigEntry[GatusDataUpdateCoordinator]
```

### TypedDict for GatusEndpoint (Claude's discretion — recommended over dataclass)

TypedDict is recommended over dataclass for `coordinator.data` values because:
- HA coordinator data is a pure value container (no methods needed)
- TypedDict works natively with dict unpacking and JSON deserialization
- Blueprint examples use both; TypedDict is lighter and matches the JSON structure

```python
from typing import TypedDict

class GatusEndpoint(TypedDict):
    key: str
    name: str
    group: str
    success: bool
    duration_ms: int
    timestamp: str
    condition_results: list[dict]
```

### manifest.json (Phase 1 complete — adds documentation beyond D-09)

```json
{
  "domain": "gatus",
  "name": "Gatus",
  "codeowners": ["@akentner"],
  "config_flow": true,
  "documentation": "https://github.com/akentner/homeassistant-gatus-integration",
  "issue_tracker": "https://github.com/akentner/homeassistant-gatus-integration/issues",
  "integration_type": "hub",
  "iot_class": "cloud_polling",
  "version": "0.1.0",
  "requirements": []
}
```

### pyproject.toml test config

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 120

[tool.mypy]
python_version = "3.14"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `hass.data[DOMAIN][entry_id]` | `entry.runtime_data` (typed generic) | HA 2024+ | Type-safe, no dict key collision, auto-cleaned on unload |
| `async_timeout.timeout()` | `asyncio.timeout()` | Python 3.11+ | No import needed; `async_timeout` module deprecated |
| `hass.data[DOMAIN]` for coordinator | `entry.runtime_data = coordinator` directly | HA 2024 (quality scale) | Simpler, typed, HA-blessed |
| Per-entity `async_update()` | `DataUpdateCoordinator` + `CoordinatorEntity` | HA core pattern | Single poll per interval regardless of entity count |

**Deprecated/outdated:**
- `async_timeout` module: replaced by `asyncio.timeout()` stdlib — do not import.
- `hass.data[DOMAIN][entry_id]`: deprecated since HA 2024+, banned per CLAUDE.md.
- `quality_scale` in manifest.json for custom integrations: hassfest warns — do not include.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | TypedDict is preferred over dataclass for `GatusEndpoint` in HA conventions | Standard Stack | Low — both work; Claude's discretion; switch if mypy reveals issues |
| A2 | `documentation` field is required by hassfest (not just recommended) | Pitfall 1 | Medium — if wrong, Phase 4 validation passes without it; adds doc URL anyway |
| A3 | All dev packages (ruff, pytest, mypy, etc.) are legitimate ecosystem tools | Package Legitimacy Audit | Low — all are well-known; slopcheck expected to return [OK] |
| A4 | `pytest-asyncio` 1.4.0 (CLAUDE.md pin) resolves against latest `pytest-homeassistant-custom-component` | Standard Stack | Medium — if wrong, uv will surface the conflict and pin to latest compatible version |

## Open Questions (RESOLVED)

1. **`config_flow: true` with no `config_flow.py` in Phase 1**
   - What we know: D-08/D-09 finalize manifest in Phase 1; Config Flow is Phase 2.
   - What's unclear: Whether a minimal stub is needed for the integration to load cleanly in real HA (not just tests).
   - RESOLVED: A functional stub `config_flow.py` IS required in Phase 1. HA's config entry machinery tries to import `config_flow` when loading any entry with `config_flow: true` in the manifest — even in tests. Without the stub, all `async_setup_entry` calls fail with "Platform gatus.config_flow not found". Additionally, `ConfigEntryAuthFailed` triggers `async_step_reauth` — the stub must include this method to prevent `UnknownStep` errors at teardown. Added `config_flow.py` stub with `async_step_user` (raises NotImplementedError) and `async_step_reauth` (returns abort) in Plan 03.

2. **GitHub repo URL for `documentation` and `issue_tracker`**
   - What we know: D-09 omits these fields; they're required/recommended.
   - What's unclear: Whether the repo is `akentner/homeassistant-gatus-integration` or another slug.
   - RESOLVED: Used `https://github.com/akentner/homeassistant-gatus-integration` as confirmed by the project directory name and codeowners (`@akentner`). Plan 01 added these fields to manifest.json.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | HA 2026.7 runtime | ✓ (system `/usr/bin/python3`) | 3.x (verify exact) | — |
| uv | Dev env management | ✓ (`~/.local/bin/uv`) | present | pip if needed |
| SSH to `haos-op3050-1` | Live-test deploy | ✓ (per CLAUDE.md) | — | — |
| `ha` CLI wrapper | Core restart | ✓ (`~/.local/bin/ha`) | — | SSH direct |

**Missing dependencies with no fallback:** none

**Missing dependencies with fallback:** none

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | YES — API key handling | Never log `api_key`/Bearer token; pass via header only |
| V3 Session Management | NO | No user sessions in this phase |
| V4 Access Control | NO | No access control layer in this phase |
| V5 Input Validation | YES — JSON response parsing | Validate response is a list; catch `ValueError`/`TypeError` from `resp.json()` |
| V6 Cryptography | NO (delegated) | TLS handled by aiohttp + CA trust store; never hand-roll TLS |

### Known Threat Patterns for (HA polling integration + aiohttp)

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| API key in logs | Information Disclosure | Log only "API key configured: yes/no"; never log the token value |
| Untrusted JSON from Gatus | Tampering | Wrap `resp.json()` in try/except; raise `UpdateFailed` on parse error (D-05) |
| SSRF via user-supplied URL | Elevation of Privilege | Config Flow (Phase 2) validates URL reachability before saving; out of Phase 1 scope |
| TLS stripping | Tampering | aiohttp uses system CA bundle; no custom SSL context; accept http:// for local Gatus |

## Sources

### Primary (HIGH confidence)
- [CITED: developers.home-assistant.io/docs/integration_fetching_data/] — DataUpdateCoordinator, `_async_update_data`, `async_config_entry_first_refresh`, error exception types
- [CITED: developers.home-assistant.io/blog/2024/04/30/store-runtime-data-inside-config-entry/] — `entry.runtime_data`, typed ConfigEntry alias, dataclass pattern
- [CITED: developers.home-assistant.io/docs/creating_integration_manifest/] — manifest.json required fields including `documentation`
- [CITED: github.com/ludeeus/integration_blueprint] — coordinator.py and __init__.py reference implementation (fetched raw)
- [VERIFIED: pypi.org] — pytest 9.0.3, ruff 0.15.15, mypy 2.1.0, pytest-cov 7.1.0, pytest-homeassistant-custom-component 0.13.334

### Secondary (MEDIUM confidence)
- [CITED: jnsgr.uk/2024/10/writing-a-home-assistant-integration/] — Working async_setup_entry and coordinator examples cross-verifying blueprint patterns
- [CITED: github.com/MatthewFlamm/pytest-homeassistant-custom-component] — Fixture list, conftest.py requirements, asyncio_mode requirement

### Tertiary (LOW confidence)
- WebSearch results for runtime_data + DataUpdateCoordinator patterns — all cross-verified with PRIMARY sources above

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all import paths verified against official HA developer docs and blueprint source
- Architecture: HIGH — patterns directly from HA developer docs and blueprint
- Pitfalls: MEDIUM-HIGH — items 1-5 verified via primary sources; Pitfall 6 (scheduling test) is an inference from success criteria gap

**Research date:** 2026-05-31
**Valid until:** 2026-06-30 (HA dev cycle is fast-moving; re-verify if HA version jumps major)
