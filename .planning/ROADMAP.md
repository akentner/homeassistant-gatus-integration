# Roadmap: homeassistant-gatus-integration

## Overview

Greenfield custom component built in strict technical dependency order: coordinator scaffold first, then the config flow that configures it, then the entity platforms that consume it, then HACS distribution metadata. Each phase must be complete before the next can start — earlier phases produce the foundation later phases build on.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Core Scaffold** - DataUpdateCoordinator, `__init__.py`, and constants that everything else depends on
- [ ] **Phase 2: Config Flow** - UI setup for URL + API key + prefix; Options Flow for scan interval
- [ ] **Phase 3: Entity Platforms** - All sensor entities (binary_sensor, response time, uptime, conditions) with device grouping
- [ ] **Phase 4: Distribution** - HACS-ready hacs.json and validated manifest.json

## Phase Details

### Phase 1: Core Scaffold
**Goal**: A loadable HA integration that polls Gatus endpoints and stores data in the coordinator — no entities yet, but the data pipeline is correct and tested
**Depends on**: Nothing (first phase)
**Requirements**: POLL-01, POLL-02, POLL-03, POLL-04
**Success Criteria** (what must be TRUE):
  1. Coordinator fetches all endpoints from `GET /api/v1/endpoints/statuses` on first refresh and stores them keyed by endpoint key
  2. When Gatus is unreachable on first refresh, `ConfigEntryNotReady` is raised and HA retries automatically
  3. When an API key is configured, every HTTP request carries `Authorization: Bearer <token>`
  4. Default scan interval is 60 seconds; coordinator re-fetches on schedule without manual trigger
  5. Integration loads and unloads cleanly — reload leaves no duplicate coordinator or stale `entry.runtime_data`
**Plans**: TBD

### Phase 2: Config Flow
**Goal**: Users can add, configure, and reconfigure a Gatus instance entirely through the HA UI, with validation preventing bad or duplicate entries
**Depends on**: Phase 1
**Requirements**: SETUP-01, SETUP-02, SETUP-03, SETUP-04, SETUP-05, SETUP-06
**Success Criteria** (what must be TRUE):
  1. User can complete the Config Flow by entering a URL and optional API key; the integration is added to HA without YAML
  2. User can set a custom `entity_id` prefix (default: `gatus_`) in Config Flow; all resulting entity object IDs use that prefix
  3. Config Flow refuses to save if the Gatus URL is not reachable (shows error, does not create entry)
  4. Config Flow refuses to save a URL already used by an existing entry (normalized, trailing slash stripped)
  5. User can change scan interval (30–300 s) via Options Flow after setup without removing and re-adding the entry
  6. Two separate Gatus instances can coexist as distinct Config Entries without conflict
**Plans**: TBD

### Phase 3: Entity Platforms
**Goal**: Every Gatus endpoint is visible in HA as a full set of four sensor entities grouped under one device per Gatus group, with stale entities cleaned up automatically
**Depends on**: Phase 2
**Requirements**: SENS-01, SENS-02, SENS-03, SENS-04, SENS-05, SENS-06, SENS-07, SENS-08, DEVICE-01, DEVICE-02, DEVICE-03, DEVICE-04
**Success Criteria** (what must be TRUE):
  1. Each Gatus endpoint produces exactly four HA entities: a binary sensor (connectivity class, on=up/off=down), a response time sensor (device_class: duration, unit: ms), an uptime sensor (7-day float %), and a conditions sensor (state: "X/Y" string)
  2. Binary sensor carries attributes: `last_check_timestamp`, `error_reason`, `response_duration_ms`, `consecutive_failures`
  3. Endpoints in the same Gatus group share one HA Device; endpoints in different groups appear under different devices
  4. Entity unique IDs use `{entry_id}_{endpoint_key}_{sensor_type}`; entity object IDs use `{prefix}{endpoint_key}_{sensor_type}`
  5. When a Gatus endpoint disappears from the API response, its corresponding HA entities are removed from the entity registry
**Plans**: TBD
**UI hint**: no

### Phase 4: Distribution
**Goal**: The integration is installable via HACS and passes all HA validator checks
**Depends on**: Phase 3
**Requirements**: DIST-01, DIST-02
**Success Criteria** (what must be TRUE):
  1. `hacs.json` is present with correct `name`, `homeassistant: "2025.1.0"`, and `hacs: "2.0.5"` fields; HACS accepts the repository
  2. `manifest.json` passes hassfest validation with all required fields present: `domain`, `name`, `codeowners`, `config_flow: true`, `integration_type: hub`, `iot_class: cloud_polling`, `version`
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Core Scaffold | 0/? | Not started | - |
| 2. Config Flow | 0/? | Not started | - |
| 3. Entity Platforms | 0/? | Not started | - |
| 4. Distribution | 0/? | Not started | - |
