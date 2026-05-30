# Technology Stack

**Project:** homeassistant-gatus-integration
**Researched:** 2026-05-30

**Sources verified against:**
- HA developer docs (home-assistant/developers.home-assistant)
- ludeeus/integration_blueprint (2026-05-28)
- HA core pyproject.toml (dev branch)
- PyPI JSON API (2026-05-30)

---

## Core Runtime

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Python | 3.14+ | Runtime | HA 2026.7 requires `>=3.14.2`. Blueprint targets `py314`. |
| homeassistant | 2026.3.2 (dev env pin) | Framework | Provides DataUpdateCoordinator, Config Flow, aiohttp session, voluptuous. Do not pin in manifest. |
| aiohttp | 3.13.5 (via HA) | HTTP client | Use `async_get_clientsession(hass)` — reuses HA's shared session. Never create standalone ClientSession. |

**Confidence: HIGH**

---

## manifest.json (minimum viable for HACS)

```json
{
  "domain": "gatus",
  "name": "Gatus",
  "codeowners": ["@your-github-username"],
  "config_flow": true,
  "documentation": "https://github.com/your-username/homeassistant-gatus-integration",
  "integration_type": "hub",
  "iot_class": "cloud_polling",
  "issue_tracker": "https://github.com/your-username/homeassistant-gatus-integration/issues",
  "version": "0.1.0",
  "requirements": []
}
```

Notes:
- `"integration_type": "hub"` — coordinator manages multiple child entities
- `"iot_class": "cloud_polling"` — URL is user-supplied; covers local and remote Gatus
- `"version"` — required for custom integrations; HACS validates this
- `"requirements": []` — no third-party pip deps; all HTTP via HA's aiohttp session
- **Do NOT include `"quality_scale"`** — for HA core integrations only; hassfest warns

---

## hacs.json

```json
{
  "name": "Gatus",
  "homeassistant": "2025.1.0",
  "hacs": "2.0.5"
}
```

- `homeassistant`: `2025.1.0` ensures Python 3.13+ runtime; safe baseline
- `hacs`: `2.0.5` is the current HACS release (2025-01-28)
- No `filename` needed — standard folder-based distribution

**Confidence: HIGH**

---

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

---

## Development Tools

| Tool | Version | Purpose |
|------|---------|---------|
| ruff | 0.15.7 (blueprint) | Lint + format (replaces flake8/isort/black) |
| pytest | 9.0.3 | Test runner |
| pytest-homeassistant-custom-component | 0.13.334 | HA fixtures: `hass`, `MockConfigEntry`, `aioclient_mock` |
| pytest-asyncio | 1.4.0 | Async test support (`asyncio_mode = auto`) |
| pytest-cov | 7.1.0 | Coverage |
| mypy | 2.1.0 | Type checking |

---

## ruff Configuration (.ruff.toml)

```toml
target-version = "py313"

[lint]
select = ["ALL"]
ignore = [
    "ANN401",  # Any allowed
    "D203",    # incompatible with formatter
    "D212",    # incompatible with formatter
    "COM812",  # incompatible with formatter
    "ISC001",  # incompatible with formatter
]

[lint.flake8-pytest-style]
fixture-parentheses = false

[lint.pyupgrade]
keep-runtime-typing = true

[lint.mccabe]
max-complexity = 25
```

---

## pytest Configuration

```ini
# pyproject.toml [tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

Required `tests/conftest.py`:
```python
import pytest

@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield
```

Without `enable_custom_integrations`, HA's loader silently ignores `custom_components/`.

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `httpx` | Not the HA integration pattern | `async_get_clientsession(hass)` |
| `requests` | Synchronous; blocks event loop; banned in HA | aiohttp |
| `async_timeout` module import | Deprecated in Python 3.11+ | `asyncio.timeout()` (stdlib) |
| `hass.data[DOMAIN][entry_id]` | Deprecated since HA 2024+; untyped | `entry.runtime_data` |
| Per-entity `async_update()` | N entities × N HTTP calls | `DataUpdateCoordinator` + `CoordinatorEntity` |
| `"quality_scale"` in manifest.json | Core integrations only; hassfest warns | Omit |

---

## Roadmap Implications

- **No third-party pip dependencies** — `requirements: []`. Entire HTTP stack from HA itself.
- **Phase 1 (Foundation)**: coordinator + config flow + one sensor entity. Coordinator pattern must be correct from the start — retrofitting touches every entity.
- **Testing**: `aioclient_mock` fixture handles all HTTP mocking. No extra libraries needed.
- **Type annotations**: Use `type MyConfigEntry = ConfigEntry[MyData]` alias pattern from blueprint. Full type safety at zero runtime cost.
