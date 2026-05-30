# Feature Landscape

**Domain:** Home Assistant custom integration — monitoring/uptime (Gatus)
**Researched:** 2026-05-30
**Confidence:** HIGH (HA developer docs, HACS docs, Context7 verified)

---

## Table Stakes

Features users expect from any HA monitoring integration. Missing = product feels broken or untrustworthy.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Config Flow (UI setup) | All modern HA integrations require it; YAML-only integrations are rejected for HACS default | Low | `async_step_user` with URL + optional API key |
| URL reachability validation in config flow | Users enter wrong URLs; fail fast, not silently at runtime | Low | Make an HTTP request before saving the entry |
| Unique entry ID on duplicate detection | HA enforces this; without it users can add the same Gatus instance twice | Low | Use URL as unique_id on the config entry |
| Binary sensor per Gatus endpoint (up/down) | Core value: connectivity status visible in HA dashboards and automations | Low | `device_class: connectivity`, on=up off=down |
| Response time sensor per endpoint | Users running uptime monitoring care about latency, not just up/down | Low | `device_class: duration`, unit ms, state_class: measurement |
| Uptime % sensor per endpoint | Standard uptime monitor metric; the Gatus API returns 7d window directly | Low | Float, no device_class, state_class: measurement |
| Attributes on binary sensor | Timestamps, error reasons, duration — needed for automations and dashboards | Low | last_check_timestamp, error_reason, response_duration_ms, consecutive_failures |
| DataUpdateCoordinator pattern | HA architectural requirement for polling integrations; single fetch per interval | Medium | Required to avoid rate-limiting and inefficiency |
| ConfigEntryNotReady on first fetch failure | HA convention; tells HA to retry setup rather than marking integration as failed forever | Low | Raise in `async_setup_entry` if coordinator refresh fails |
| Options Flow for scan interval | Users need to tune polling without re-adding the integration | Low | 30–300 s range; HA convention for runtime-adjustable settings |
| Unique entity IDs | Required for entity registry (rename, disable, area assignment in UI) | Low | Pattern: `{entry_id}_{endpoint_key}_{sensor_type}` |
| Device grouping by Gatus group | Mirrors Gatus structure; allows logical grouping in HA device registry | Low | One HA Device per Gatus group + config entry |
| HACS manifest (hacs.json) | Required for HACS distribution; must be in repo root | Low | `name`, `homeassistant` min version |
| manifest.json with required fields | hassfest validation gates HACS inclusion | Low | domain, name, version, codeowners, documentation, issue_tracker, iot_class |
| English strings/translations | HA renders config flow UI from strings.json/translations/en.json | Low | Config flow step labels, errors, options labels |
| Multiple instances support | Users may run multiple Gatus instances (prod, staging, homelab); HA config entries naturally support this | Low | No global state; all state per config entry |

---

## Differentiators

Features that raise the integration above "it works" to "it's a good integration."

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Conditions sensor per endpoint | Gatus returns pass/fail counts per check; exposes finer-grained health data unavailable in other monitoring integrations | Low | Integer or string "X/Y passed", attribute with individual condition results |
| Translation key on entity names | Enables future localization; marks the integration as following modern HA patterns (post-2023.1) | Low | `translation_key` property on each entity class |
| Reconfigure flow | Allows URL or API key to change without deleting and re-adding the integration | Low-Med | `async_step_reconfigure` in config_flow.py |
| Diagnostics platform | Download-able snapshot of coordinator data for bug reports; expected by power users | Low | `diagnostics.py` with `async_get_config_entry_diagnostics` |
| `entry.runtime_data` usage | Modern HA pattern (replaces `hass.data[DOMAIN]`); type-safe, auto-cleanup | Low | Use `type GatusConfigEntry = ConfigEntry[GatusDataUpdateCoordinator]` |
| Connection class in manifest | `iot_class: local_polling` vs `cloud_polling` — honest declaration helps users understand connectivity model | Low | Declare correctly in manifest.json |
| CI: HACS Action + hassfest | Automated quality gate; required for HACS default store inclusion | Low | `.github/workflows/validate.yml` with both actions |
| State class on sensors | Required for HA long-term statistics and energy dashboard compat | Low | `state_class: measurement` on response time and uptime sensors |
| Configurable entity_id prefix | Prevents collisions when multiple Gatus instances exist | Low | Implemented in coordinator or sensor naming |

---

## Anti-Features

Features to explicitly NOT build.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Polling interval in config flow step | HA pylint rule W7407 explicitly bans this — hassfest will fail | Put scan_interval in Options Flow only |
| `hass.data[DOMAIN]` for coordinator storage | Deprecated pattern; type-unsafe, collision-prone | Use `entry.runtime_data` |
| Individual `update()` calls on each entity | Defeats the coordinator pattern; causes N API calls per interval instead of 1 | All entities share coordinator, update via `CoordinatorEntity` |
| Gatus config management (create/edit monitors) | Gatus has no write API for monitor definitions; this is out of scope | Read-only integration |
| Webhook / push from Gatus | Gatus does not support outbound webhooks to HA; polling only | Polling via coordinator |
| Historical data storage | HA recorder handles history; the integration should not cache API data beyond what the coordinator holds | Let coordinator data expire naturally |
| YAML configuration (no config flow) | YAML-only integrations cannot be submitted to HACS default; HA is moving away from YAML | Config flow is the only setup path |
| Sensor for each individual condition result | Condition results vary per Gatus endpoint config; dynamic entity creation breaks HA entity registry stability | Surface as attributes, not entities |
| Separate aiohttp session per coordinator | Wasteful; HA provides `async_get_clientsession(hass)` | Use the HA-managed session |

---

## Feature Dependencies

```
Config Flow (URL + API key)
  → Config Entry created
    → DataUpdateCoordinator (uses URL + API key)
      → Binary Sensor entities (one per Gatus endpoint)
      → Response Time sensors (one per Gatus endpoint)
      → Uptime sensors (one per Gatus endpoint)
      → Conditions sensor (one per Gatus endpoint)

Options Flow (scan interval)
  → Re-initializes coordinator with new interval

Device Registry
  → Requires: unique entry ID, group-level device identifiers
  → Enables: area assignment, device page in UI

Entity Registry
  → Requires: unique entity IDs per entity
  → Enables: rename, disable, area assignment per entity

Diagnostics
  → Requires: coordinator running with data
  → Enables: downloadable debug snapshot

CI / HACS default inclusion
  → Requires: hacs.json, manifest.json with all fields, GitHub Actions passing
```

---

## MVP Recommendation

Prioritize for initial release:

1. Config Flow with URL validation and duplicate detection
2. DataUpdateCoordinator with ConfigEntryNotReady
3. Binary Sensor + Response Time + Uptime sensors per endpoint (the core value)
4. Attributes on binary sensor (timestamp, error_reason, duration, consecutive_failures)
5. Device grouping by Gatus group
6. Unique entity IDs
7. Options Flow for scan interval
8. HACS-ready manifest files + CI actions

Defer to follow-up:

- Conditions sensor: adds value but not table stakes; add after core entities validated
- Diagnostics: useful but not blocking initial release
- Reconfigure flow: nice-to-have; users can delete + re-add for URL changes
- Translation keys: add when translation files are contributed; skeleton is low-effort now

---

## HA Quality Scale Alignment (Informational)

The integration should target **Bronze** tier minimum (HACS default requires it passing hassfest, which is effectively Bronze). Key Bronze requirements that map directly to features above:

- Config flow (not YAML)
- Unique ID on config entry
- Unique IDs on all entities
- ConfigEntryNotReady on failed setup
- `runtime_data` instead of `hass.data`
- Correct `iot_class` in manifest

Silver/Gold extras (for later):
- Diagnostics platform (Silver)
- Reconfigure flow (Silver)
- Full test coverage with pytest-homeassistant-custom-component (Silver/Gold)

---

## Comparable Integrations in HA Ecosystem

**Uptime Kuma** (now a core HA integration) uses plain sensors with string states (up/down/pending/maintenance) rather than binary sensors. This is a deliberate design choice there because Uptime Kuma has more status states. For Gatus, which has a boolean `success` field per result, binary sensor is the natural fit. The Uptime Kuma pattern of creating a global status binary sensor via a template is a user-space workaround that our binary sensor approach makes unnecessary.

---

## Sources

- HACS documentation (Context7: /hacs/documentation) — hacs.json format, HACS validation requirements, repository structure
- Home Assistant core docs (Context7: /home-assistant/core) — quality scale rules, runtime_data pattern, pylint W7407 (no polling in config flow)
- Home Assistant website docs (Context7: /home-assistant/home-assistant.io) — quality scale tiers, Uptime Kuma integration patterns, binary sensor connectivity class, diagnostics platform changelog
- pytest-homeassistant-custom-component docs (Context7: /matthewflamm/pytest-homeassistant-custom-component) — MockConfigEntry, device/entity registry testing patterns
- CLAUDE.md project context (PROJECT.md) — confirmed requirements and out-of-scope items
