# Project: homeassistant-gatus-integration

## What This Is

Home Assistant custom integration that polls the Gatus monitoring API and exposes endpoint health as native HA sensor entities. Each Gatus endpoint becomes a set of HA entities: a binary sensor (up/down), a response time sensor, an uptime percentage sensor, and a conditions sensor.

## Core Value

One Gatus instance → full HA entity set per endpoint, queryable in automations and dashboards without any intermediate plumbing.

## Who It's For

Home Assistant users running self-hosted Gatus for uptime monitoring who want service health visible alongside other home automation data.

## Context

- Greenfield custom component, no prior code
- Target runtime: Home Assistant with aiohttp async HTTP
- Distribution: HACS-ready (hacs.json) + manual install via SCP/symlink
- Development target: haos-op3050-1 (Tailscale SSH)

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] User can add a Gatus instance via Config Flow (URL + optional API key)
- [ ] User can configure entity_id prefix (default: `gatus_`)
- [ ] Each Gatus endpoint produces a Binary Sensor (connectivity class, on=up, off=down)
- [ ] Binary Sensor carries attributes: last_check_timestamp, error_reason, response_duration_ms, consecutive_failures
- [ ] Each Gatus endpoint produces a Response Time sensor (ms int, device_class: duration)
- [ ] Each Gatus endpoint produces an Uptime % sensor (float, 7-day window)
- [ ] Each Gatus endpoint produces a Conditions sensor (passed/total condition count)
- [ ] Endpoints within the same Gatus group share one HA Device
- [ ] Polling interval default 60 s, configurable via Options Flow (30–300 s)
- [ ] API key sent as `Authorization: Bearer <token>` header when provided
- [ ] Integration raises ConfigEntryNotReady if first refresh fails
- [ ] Multiple Gatus instances supported (separate Config Entries)
- [ ] HACS distribution: hacs.json + proper manifest.json

### Out of Scope

- Pushing alerts/notifications from HA to Gatus — not a Gatus API feature
- Gatus config management (creating/editing Gatus monitors from HA)
- Historical data storage beyond what Gatus API returns

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| DataUpdateCoordinator | HA best practice for polling integrations — single fetch per interval | Confirmed |
| Binary Sensor for status | Standard HA connectivity pattern, works with existing dashboards/automations | Confirmed |
| Device = Gatus group | Groups endpoints logically, mirrors Gatus structure | Confirmed |
| Configurable entity_id prefix | Avoids conflicts when multiple Gatus instances exist | Confirmed |
| HACS + manual | Broadest installation reach | Confirmed |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-30 after initialization*
