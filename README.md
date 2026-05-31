# Gatus Integration for Home Assistant

Polls the [Gatus](https://github.com/TwiN/gatus) monitoring API and exposes endpoint health as native Home Assistant sensor entities. Each Gatus endpoint becomes a set of HA entities — queryable in automations and dashboards without any intermediate plumbing.

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → click the three-dot menu → **Custom repositories**
3. Add `https://github.com/akentner/homeassistant-gatus-integration` as an **Integration**
4. Search for **Gatus** and click **Download**
5. Restart Home Assistant

### Manual

1. Copy `custom_components/gatus/` into your HA config directory:
   ```bash
   scp -r custom_components/gatus your-ha-host:/config/custom_components/
   ```
2. Restart Home Assistant

## Configuration

Go to **Settings → Integrations → Add Integration → Gatus**.

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| URL | Yes | — | Base URL of your Gatus instance (e.g. `https://status.example.com`) |
| API Key | No | — | Bearer token if Gatus authentication is enabled |
| Entity prefix | No | `gatus_` | Prefix for all entity object IDs |
| Scan interval | No | 60 s | How often to poll in seconds (30–300 s) |

The scan interval can be changed after setup via **Options** without removing the integration.

Multiple Gatus instances can coexist as separate config entries.

## Entities

For each Gatus endpoint, four entities are created:

| Entity | Type | Device Class | Unit | Description |
|--------|------|--------------|------|-------------|
| `{prefix}{key}_status` | Binary Sensor | connectivity | — | `on` = up, `off` = down |
| `{prefix}{key}_response_time` | Sensor | duration | ms | Last response time in milliseconds |
| `{prefix}{key}_uptime` | Sensor | — | % | Uptime percentage based on available results |
| `{prefix}{key}_conditions` | Sensor | — | — | Condition results, e.g. `3/3` (passed/total) |

### Binary Sensor Attributes

| Attribute | Description |
|-----------|-------------|
| `last_check_timestamp` | ISO timestamp of the latest check |
| `error_reason` | Which condition failed, or `null` if the endpoint is up |
| `response_duration_ms` | Last check duration in milliseconds |
| `consecutive_failures` | Count of consecutive failed checks |

### Conditions Sensor Attributes

| Attribute | Description |
|-----------|-------------|
| `condition_details` | List of individual condition results: `[{condition, success}, ...]` |

## Device Grouping

Endpoints in the same Gatus group share one HA Device. The device name equals the Gatus group name. Endpoints in different groups appear under different devices.

When a Gatus endpoint is removed from the server, its corresponding HA entities are removed from the entity registry automatically on the next coordinator refresh.

## Requirements

- Home Assistant 2025.1.0 or later
- A running Gatus instance reachable from your Home Assistant host

## License

MIT
