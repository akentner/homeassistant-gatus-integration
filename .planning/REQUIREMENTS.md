# Requirements: homeassistant-gatus-integration

## v1 Requirements

### Setup & Configuration

- [x] **SETUP-01**: User can add a Gatus instance via Config Flow (URL, optional API key, optional entity_id prefix)
- [x] **SETUP-02**: Entity_id prefix is configurable in Config Flow (default: `gatus_`, applied to all entity object IDs)
- [x] **SETUP-03**: Config Flow validates URL reachability before saving
- [x] **SETUP-04**: Config Flow rejects duplicate Gatus URL (normalized, strips trailing slash)
- [ ] **SETUP-05**: User can update scan interval (30–300 s) via Options Flow after setup
- [ ] **SETUP-06**: Multiple Gatus instances can coexist as separate Config Entries

### Data Polling

- [x] **POLL-01**: Integration polls `GET /api/v1/endpoints/statuses` via shared aiohttp session
- [x] **POLL-02**: API key sent as `Authorization: Bearer <token>` when provided
- [x] **POLL-03**: Coordinator raises `ConfigEntryNotReady` if first refresh fails
- [x] **POLL-04**: Default scan interval is 60 s

### Entities — Binary Sensor

- [ ] **SENS-01**: Each Gatus endpoint produces one Binary Sensor (device_class: connectivity; on=up, off=down)
- [ ] **SENS-02**: Binary Sensor carries attribute `last_check_timestamp` (ISO timestamp of latest result)
- [ ] **SENS-03**: Binary Sensor carries attribute `error_reason` (which condition failed, or null if up)
- [ ] **SENS-04**: Binary Sensor carries attribute `response_duration_ms` (last check duration in ms)
- [ ] **SENS-05**: Binary Sensor carries attribute `consecutive_failures` (count of consecutive failed checks)

### Entities — Sensors

- [ ] **SENS-06**: Each Gatus endpoint produces one Response Time sensor (device_class: duration; unit: ms; int)
- [ ] **SENS-07**: Each Gatus endpoint produces one Uptime % sensor (7-day window; float; state_class: measurement)
- [ ] **SENS-08**: Each Gatus endpoint produces one Conditions sensor (state: "X/Y" string — passed/total conditions)

### Device & Entity Structure

- [ ] **DEVICE-01**: Endpoints in the same Gatus group share one HA Device (identifiers: `{DOMAIN, entry_id + group_name}`)
- [ ] **DEVICE-02**: Entity unique IDs use format `{entry_id}_{endpoint_key}_{sensor_type}`
- [ ] **DEVICE-03**: Entity object IDs use format `{prefix}{endpoint_key}_{sensor_type}` where prefix is from SETUP-02
- [ ] **DEVICE-04**: Entities removed from HA when the corresponding Gatus endpoint disappears (active reconciliation via entity registry)

### Distribution

- [ ] **DIST-01**: `hacs.json` present with `name`, `homeassistant: "2025.1.0"`, `hacs: "2.0.5"`
- [ ] **DIST-02**: `manifest.json` includes all required fields: `domain`, `name`, `codeowners`, `config_flow: true`, `integration_type: hub`, `iot_class: cloud_polling`, `version`

---

## v2 Requirements (deferred)

- Conditions sensor with per-condition breakdown (individual pass/fail per condition name)
- Diagnostics platform (HA quality scale Silver requirement)
- Reconfigure flow (change URL/API key without removing entry)
- Translation keys for entity names (multi-language support beyond English)
- Pagination support for Gatus instances with 100+ endpoints

---

## Out of Scope

- Push alerts from HA to Gatus — Gatus has no inbound webhook/alert API
- Gatus config management (creating/editing Gatus monitors from HA)
- Historical data storage beyond what the Gatus API returns in the statuses response

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| POLL-01 | Phase 1 (Core Scaffold) | Complete |
| POLL-02 | Phase 1 (Core Scaffold) | Complete |
| POLL-03 | Phase 1 (Core Scaffold) | Complete |
| POLL-04 | Phase 1 (Core Scaffold) | Complete |
| SETUP-01 | Phase 2 (Config Flow) | Complete |
| SETUP-02 | Phase 2 (Config Flow) | Complete |
| SETUP-03 | Phase 2 (Config Flow) | Complete |
| SETUP-04 | Phase 2 (Config Flow) | Complete |
| SETUP-05 | Phase 2 (Config Flow) | Pending |
| SETUP-06 | Phase 2 (Config Flow) | Pending |
| SENS-01 | Phase 3 (Entity Platforms) | Pending |
| SENS-02 | Phase 3 (Entity Platforms) | Pending |
| SENS-03 | Phase 3 (Entity Platforms) | Pending |
| SENS-04 | Phase 3 (Entity Platforms) | Pending |
| SENS-05 | Phase 3 (Entity Platforms) | Pending |
| SENS-06 | Phase 3 (Entity Platforms) | Pending |
| SENS-07 | Phase 3 (Entity Platforms) | Pending |
| SENS-08 | Phase 3 (Entity Platforms) | Pending |
| DEVICE-01 | Phase 3 (Entity Platforms) | Pending |
| DEVICE-02 | Phase 3 (Entity Platforms) | Pending |
| DEVICE-03 | Phase 3 (Entity Platforms) | Pending |
| DEVICE-04 | Phase 3 (Entity Platforms) | Pending |
| DIST-01 | Phase 4 (Distribution) | Pending |
| DIST-02 | Phase 4 (Distribution) | Pending |

---

## Design Decisions

| Area | Decision |
|------|----------|
| Status sensor type | Binary Sensor (connectivity class) — matches Gatus boolean `success` field |
| Conditions value format | String "X/Y" (passed/total) — shows both numerator and denominator at a glance |
| Entity removal | Active reconciliation — stale entities removed via `entity_registry.async_remove` |
| Entity_id prefix | Config Flow field (default: `gatus_`) — supports multiple instances without collisions |
| Duration unit | Milliseconds — Gatus returns nanoseconds, divide by 1,000,000 |
| Uptime data source | `results` array from statuses endpoint — verify `?duration` param at implementation |
