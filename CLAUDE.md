# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

Home Assistant custom integration that polls the [Gatus](https://github.com/TwiN/gatus) monitoring API and exposes endpoint health as HA sensor entities.

## Target Structure

```
custom_components/gatus/
├── __init__.py          # Integration setup, forward to platforms
├── manifest.json        # HA integration metadata
├── config_flow.py       # UI setup: URL + optional API key
├── const.py             # DOMAIN, platform names, scan interval
├── coordinator.py       # DataUpdateCoordinator — single polling point
├── sensor.py            # SensorEntity subclasses per Gatus endpoint
├── strings.json         # Config flow strings (en)
└── translations/
    └── en.json
```

## Gatus API

Base URL configured by user (e.g. `https://status.example.com`).

Key endpoints:
- `GET /api/v1/endpoints/statuses` — all endpoints with recent results
- `GET /api/v1/endpoints/{key}/statuses` — single endpoint history

Each endpoint object has:
```json
{
  "key": "core_my-service",
  "name": "my-service",
  "group": "core",
  "results": [
    {
      "success": true,
      "duration": 42000000,
      "conditionResults": [...],
      "timestamp": "2024-01-01T00:00:00Z"
    }
  ]
}
```

Auth: optional `Authorization: Bearer <token>` header.

## Architecture

**Coordinator pattern** (required for polling integrations):
- `GatusDataUpdateCoordinator` in `coordinator.py` fetches all endpoints once per interval
- Sensors receive data via `coordinator.data[endpoint_key]`
- Default scan interval: 60 s (configurable via Options Flow)

**One entity per Gatus endpoint**, yielding these sensors:
| Sensor | State/Value | Device class |
|--------|------------|--------------|
| Status | `up` / `down` | `connectivity` (binary) or plain sensor |
| Response time | ms (int) | `duration` |
| Uptime (7d) | % float | — |

**Config entry data**: `{"url": "https://...", "api_key": "optional"}`.

## Development Commands

```bash
# Install HA dev deps (run once)
pip install homeassistant

# Validate manifest.json
python -m homeassistant --script check_config

# Run integration tests
pytest tests/ -v

# Lint
ruff check custom_components/gatus/
ruff format custom_components/gatus/

# Type check
mypy custom_components/gatus/
```

For live testing, symlink or copy `custom_components/gatus/` into the HA config dir on `haos-op3050-1`:
```bash
scp -r custom_components/gatus haos-op3050-1:/config/custom_components/
ha core restart   # uses ~/.local/bin/ha wrapper
```

## HA Integration Conventions

- Use `DataUpdateCoordinator` — never poll in individual entity `update()` calls.
- Config Flow must implement `async_step_user`; validate URL reachability before saving.
- Use `ConfigEntryNotReady` if coordinator first refresh fails.
- Unique IDs: `f"{config_entry.entry_id}_{endpoint_key}_{sensor_type}"`.
- Device info: group per Gatus group name, identifiers by entry + group.
- `manifest.json` must declare `"iot_class": "cloud_polling"` (or `local_polling`).

## Testing

Use `pytest-homeassistant-custom-component` (hacs/hacs-test scaffolding):
```bash
pip install pytest-homeassistant-custom-component
pytest tests/ -v --cov=custom_components/gatus
```

Mock `aiohttp.ClientSession` for coordinator tests; use `MockConfigEntry` from HA test helpers.

<!-- GSD:project-start source:PROJECT.md -->
## Project

**Project: homeassistant-gatus-integration**

Home Assistant custom integration that polls the Gatus monitoring API and exposes endpoint health as native HA sensor entities. Each Gatus endpoint becomes a set of HA entities: a binary sensor (up/down), a response time sensor, an uptime percentage sensor, and a conditions sensor.

**Core Value:** One Gatus instance → full HA entity set per endpoint, queryable in automations and dashboards without any intermediate plumbing.
<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->
## Technology Stack

- HA developer docs (home-assistant/developers.home-assistant)
- ludeeus/integration_blueprint (2026-05-28)
- HA core pyproject.toml (dev branch)
- PyPI JSON API (2026-05-30)
## Core Runtime
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.14+ | Runtime | HA 2026.7 requires `>=3.14.2`. Blueprint targets `py314`. |
| homeassistant | 2026.3.2 (dev env pin) | Framework | Provides DataUpdateCoordinator, Config Flow, aiohttp session, voluptuous. Do not pin in manifest. |
| aiohttp | 3.13.5 (via HA) | HTTP client | Use `async_get_clientsession(hass)` — reuses HA's shared session. Never create standalone ClientSession. |
## manifest.json (minimum viable for HACS)
- `"integration_type": "hub"` — coordinator manages multiple child entities
- `"iot_class": "cloud_polling"` — URL is user-supplied; covers local and remote Gatus
- `"version"` — required for custom integrations; HACS validates this
- `"requirements": []` — no third-party pip deps; all HTTP via HA's aiohttp session
- **Do NOT include `"quality_scale"`** — for HA core integrations only; hassfest warns
## hacs.json
- `homeassistant`: `2025.1.0` ensures Python 3.13+ runtime; safe baseline
- `hacs`: `2.0.5` is the current HACS release (2025-01-28)
- No `filename` needed — standard folder-based distribution
## Architecture Libraries (from `homeassistant` package — no pip installs)
| Component | Import path | Purpose |
|-----------|-------------|---------|
| `DataUpdateCoordinator` | `homeassistant.helpers.update_coordinator` | Single polling point for all entities |
| `CoordinatorEntity` | `homeassistant.helpers.update_coordinator` | Entity base: wires `should_poll=False`, availability, update subscription |
| `ConfigFlow` | `homeassistant.config_entries` | UI setup wizard |
| `OptionsFlow` | `homeassistant.config_entries` | Polling interval config post-setup |
| `SensorEntity` | `homeassistant.components.sensor` | Response time (ms), uptime % (float), condition count |
| `BinarySensorEntity` | `homeassistant.components.binary_sensor` | Up/down; `BinarySensorDeviceClass.CONNECTIVITY` |
| `DeviceInfo` | `homeassistant.helpers.device_registry` | Group entities by Gatus group name |
| `ConfigEntryNotReady` | `homeassistant.exceptions` | First-refresh failure → HA retries automatically |
| `ConfigEntryAuthFailed` | `homeassistant.exceptions` | 401/403 → triggers re-auth flow |
| `async_get_clientsession` | `homeassistant.helpers.aiohttp_client` | Get shared aiohttp session |
| `selector` | `homeassistant.helpers.selector` | Type-safe config flow form fields |
## Development Tools
| Tool | Version | Purpose |
|------|---------|---------|
| ruff | 0.15.7 (blueprint) | Lint + format (replaces flake8/isort/black) |
| pytest | 9.0.3 | Test runner |
| pytest-homeassistant-custom-component | 0.13.334 | HA fixtures: `hass`, `MockConfigEntry`, `aioclient_mock` |
| pytest-asyncio | 1.4.0 | Async test support (`asyncio_mode = auto`) |
| pytest-cov | 7.1.0 | Coverage |
| mypy | 2.1.0 | Type checking |
## ruff Configuration (.ruff.toml)
## pytest Configuration
# pyproject.toml [tool.pytest.ini_options]
## What NOT to Use
| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `httpx` | Not the HA integration pattern | `async_get_clientsession(hass)` |
| `requests` | Synchronous; blocks event loop; banned in HA | aiohttp |
| `async_timeout` module import | Deprecated in Python 3.11+ | `asyncio.timeout()` (stdlib) |
| `hass.data[DOMAIN][entry_id]` | Deprecated since HA 2024+; untyped | `entry.runtime_data` |
| Per-entity `async_update()` | N entities × N HTTP calls | `DataUpdateCoordinator` + `CoordinatorEntity` |
| `"quality_scale"` in manifest.json | Core integrations only; hassfest warns | Omit |
## Roadmap Implications
- **No third-party pip dependencies** — `requirements: []`. Entire HTTP stack from HA itself.
- **Phase 1 (Foundation)**: coordinator + config flow + one sensor entity. Coordinator pattern must be correct from the start — retrofitting touches every entity.
- **Testing**: `aioclient_mock` fixture handles all HTTP mocking. No extra libraries needed.
- **Type annotations**: Use `type MyConfigEntry = ConfigEntry[MyData]` alias pattern from blueprint. Full type safety at zero runtime cost.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->
## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
