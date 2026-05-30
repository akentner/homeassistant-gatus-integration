# Architecture Patterns: Home Assistant Polling Custom Integration

**Domain:** HA custom integration — REST API polling
**Researched:** 2026-05-30
**Confidence:** HIGH (sourced from official HA developer documentation via Context7)

---

## Recommended Architecture

The canonical HA pattern for a REST-polling integration is:

```
Config Flow (one-time setup)
        |
        v
  Config Entry (persisted credential + options store)
        |
        v
  __init__.py: async_setup_entry
        |
        +-- creates GatusApiClient (aiohttp session)
        +-- creates GatusDataUpdateCoordinator
        +-- calls coordinator.async_config_entry_first_refresh()
        +-- calls hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        |
        v
  sensor.py / binary_sensor.py: async_setup_entry
        |
        +-- retrieves coordinator from hass.data[DOMAIN][entry.entry_id]
        +-- creates entity instances (one set per Gatus endpoint)
        +-- calls async_add_entities(...)
        |
        v
  Entities (CoordinatorEntity subclasses)
        |
        +-- subscribe to coordinator updates automatically
        +-- read coordinator.data[endpoint_key] on each update
        +-- write state via async_write_ha_state()
```

Every 60 s (configurable), the coordinator fires one HTTP request; all entities receive the new data via callback — no per-entity polling.

---

## Component Boundaries

| Component | File | Responsibility | Communicates With |
|-----------|------|---------------|-------------------|
| Config Flow | `config_flow.py` | Collects URL + API key from user; validates connectivity; persists config entry; exposes Options Flow for interval | HA Config Entry system |
| Integration init | `__init__.py` | Creates API client and coordinator on entry setup; forwards platforms; handles unload cleanup | Coordinator, Config Entry, hass.data |
| API client | `coordinator.py` (or `api.py`) | Wraps aiohttp; builds request with Bearer token if present; parses JSON response | External Gatus API (HTTP) |
| Coordinator | `coordinator.py` | Subclass of `DataUpdateCoordinator`; calls API client in `_async_update_data`; stores parsed data dict keyed by endpoint key | API client, all entity classes |
| Sensor entities | `sensor.py` | One class per sensor type (response time, uptime, conditions); reads from `coordinator.data[endpoint_key]`; exposes `native_value`, `device_info`, `unique_id` | Coordinator (read-only) |
| Binary sensor entities | `binary_sensor.py` | Status entity; `is_on` = `coordinator.data[endpoint_key]["success"]`; extra state attributes (timestamp, error reason, duration, consecutive failures) | Coordinator (read-only) |
| Constants | `const.py` | DOMAIN, PLATFORMS list, DEFAULT_SCAN_INTERVAL, CONF_* keys | All files import from here |
| Strings / translations | `strings.json`, `translations/en.json` | Config flow and entity label text | HA UI rendering |
| HACS metadata | `hacs.json` | Distribution metadata for HACS | HACS validator |

---

## Data Flow

### Setup phase (runs once per config entry load)

```
HA core loads config entry
  -> __init__.async_setup_entry(hass, entry)
     -> build GatusApiClient(url, api_key)
     -> build GatusDataUpdateCoordinator(hass, client, interval)
     -> hass.data[DOMAIN][entry.entry_id] = coordinator
     -> await coordinator.async_config_entry_first_refresh()
        -> calls _async_update_data()
        -> stores result: dict[str, endpoint_data] in coordinator.data
        -> raises ConfigEntryNotReady on failure (HA retries later)
     -> await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        -> sensor.async_setup_entry(hass, entry, async_add_entities)
           -> coordinator = hass.data[DOMAIN][entry.entry_id]
           -> async_add_entities([GatusResponseTimeSensor(coordinator, key), ...])
        -> binary_sensor.async_setup_entry(...)
           -> async_add_entities([GatusStatusBinarySensor(coordinator, key), ...])
```

### Steady-state polling (runs every scan_interval)

```
HA scheduler fires
  -> coordinator._async_update_data()
     -> GatusApiClient.async_get_all_statuses()
        -> GET /api/v1/endpoints/statuses
        -> returns list of endpoint dicts
     -> coordinator.data = {ep["key"]: ep for ep in endpoints}
  -> coordinator notifies all subscribers
     -> each entity._handle_coordinator_update() fires
        -> entity reads coordinator.data[self._endpoint_key]
        -> entity sets _attr_* attributes
        -> entity.async_write_ha_state()
```

### Options change (user adjusts scan interval)

```
User changes interval in Options Flow
  -> config_entry.options updated
  -> integration listens via entry.async_on_unload(
         entry.add_update_listener(async_reload_entry))
  -> HA unloads and reloads the config entry
  -> coordinator re-created with new update_interval
```

---

## File Structure

```
custom_components/gatus/
├── __init__.py          # async_setup_entry, async_unload_entry, PLATFORMS
├── manifest.json        # domain, iot_class, config_flow: true, version
├── hacs.json            # name, render_readme
├── config_flow.py       # GatusConfigFlow (async_step_user), GatusOptionsFlow
├── const.py             # DOMAIN, PLATFORMS, DEFAULT_SCAN_INTERVAL, CONF_*
├── coordinator.py       # GatusApiClient, GatusDataUpdateCoordinator
├── binary_sensor.py     # GatusStatusBinarySensor (async_setup_entry + class)
├── sensor.py            # GatusResponseTimeSensor, GatusUptimeSensor,
│                        # GatusConditionsSensor (async_setup_entry + classes)
├── strings.json         # Config/options flow strings
└── translations/
    └── en.json          # Same strings for HA UI
```

A separate `api.py` is optional — the client is small enough to live in `coordinator.py`. Splitting it out improves testability because coordinator tests can mock the client without patching aiohttp directly.

---

## unique_id, device_info, and Entity Registration

### unique_id

Each entity needs a stable unique ID so HA can persist its registry entry across restarts and renames.

```
Pattern: f"{config_entry.entry_id}_{endpoint_key}_{sensor_type}"

Examples:
  "abc123_core_my-service_binary_sensor"
  "abc123_core_my-service_response_time"
  "abc123_core_my-service_uptime_7d"
  "abc123_core_my-service_conditions"
```

`config_entry.entry_id` scopes the unique_id to this Gatus instance, enabling multiple Gatus instances without collision. `endpoint_key` is the Gatus-assigned `key` field (e.g. `core_my-service`). `sensor_type` is a fixed string per entity class.

### device_info

Each entity must declare `_attr_device_info`. Device grouping follows Gatus group names — all endpoints in the same group share one HA device.

```python
DeviceInfo(
    identifiers={(DOMAIN, f"{config_entry.entry_id}_{group_name}")},
    name=group_name,
    manufacturer="Gatus",
    configuration_url=config_entry.data[CONF_URL],
)
```

`identifiers` uniquely identifies the device. Using `(DOMAIN, entry_id + group)` allows the same Gatus group name to appear in multiple Gatus instances without collision.

### Entity registration flow

1. Entity class sets `_attr_unique_id` and `_attr_device_info` in `__init__`.
2. `async_add_entities` submits entity to HA.
3. HA entity registry checks if an entry with that `unique_id` exists.
   - First time: creates registry entry, assigns `entity_id` (e.g. `binary_sensor.gatus_core_my_service`).
   - Subsequent startups: restores existing `entity_id` even if the user renamed it.
4. HA device registry checks `identifiers` and creates or links to existing device.
5. Entity is marked available/unavailable based on `CoordinatorEntity.available` (which reflects coordinator last-update success).

### _attr_has_entity_name = True

Set this on all entity classes. With this flag, HA constructs the display name as `"{device_name} {entity_name}"` automatically. This is the current HA quality scale requirement. The entity name should then be the sensor type only (e.g. "Response Time", "Status", "Uptime (7d)").

---

## Patterns to Follow

### CoordinatorEntity base class

All entity classes inherit from both `CoordinatorEntity[GatusDataUpdateCoordinator]` and their platform entity class. This provides `should_poll = False`, automatic update subscription, and `available` reflecting coordinator health.

```python
class GatusStatusBinarySensor(
    CoordinatorEntity[GatusDataUpdateCoordinator],
    BinarySensorEntity,
):
    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator, config_entry, endpoint_key, group):
        super().__init__(coordinator)
        self._endpoint_key = endpoint_key
        self._attr_unique_id = f"{config_entry.entry_id}_{endpoint_key}_binary_sensor"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{config_entry.entry_id}_{group}")},
            name=group,
            manufacturer="Gatus",
            configuration_url=config_entry.data[CONF_URL],
        )

    @property
    def is_on(self) -> bool | None:
        data = self.coordinator.data.get(self._endpoint_key)
        if not data or not data.get("results"):
            return None
        return data["results"][0]["success"]

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data.get(self._endpoint_key, {})
        results = data.get("results", [{}])
        latest = results[0] if results else {}
        return {
            "last_check_timestamp": latest.get("timestamp"),
            "response_duration_ms": latest.get("duration", 0) // 1_000_000,
            "consecutive_failures": sum(1 for r in results if not r.get("success")),
            "error_reason": None if latest.get("success") else latest.get("errors"),
        }
```

### SensorEntityDescription pattern

Use `SensorEntityDescription` dataclasses to avoid repeating boilerplate for each sensor type. Define a tuple of descriptions and iterate to create entities:

```python
SENSOR_DESCRIPTIONS: tuple[GatusSensorDescription, ...] = (
    GatusSensorDescription(
        key="response_time",
        name="Response Time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MILLISECONDS,
        value_fn=lambda ep: ep["results"][0]["duration"] // 1_000_000,
    ),
    GatusSensorDescription(
        key="uptime_7d",
        name="Uptime (7d)",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda ep: _calc_uptime(ep["results"]),
    ),
    ...
)
```

### hass.data storage convention

```python
# In __init__.py async_setup_entry:
hass.data.setdefault(DOMAIN, {})
hass.data[DOMAIN][entry.entry_id] = coordinator

# In async_unload_entry:
if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
    hass.data[DOMAIN].pop(entry.entry_id)
return unload_ok
```

### Handling dynamic endpoint list

Gatus endpoints can appear/disappear between polls. Two strategies:

1. **Static at setup time** (simpler): entity list fixed at first refresh; removed endpoints become unavailable.
2. **Dynamic with `async_add_entities`**: store `async_add_entities` callback on coordinator; add new entities on coordinator update if new keys appear.

Strategy 1 is correct for v1 — entities for endpoints that disappear will show as unavailable (coordinator data won't have their key), which is the right UX signal.

---

## Anti-Patterns to Avoid

### Per-entity polling

Never call the Gatus API inside an entity's `async_update` method. All data fetching must go through the coordinator. HA quality scale requires this.

### Blocking calls in async context

The aiohttp session must be used with `async with` and `await`. Never use `requests` (synchronous) in an async integration.

### Missing ConfigEntryNotReady

If the first coordinator refresh fails (Gatus unreachable), `__init__.py` must let the exception propagate as `ConfigEntryNotReady`. Swallowing it would cause the integration to set up with empty data.

### Hardcoded entity_id strings

Never construct `entity_id` directly (e.g. `sensor.gatus_something`). Assign `unique_id` and let HA assign entity_id. Users can override entity_id in the UI.

### Storing mutable API objects on hass.data across reloads

Always clean up `hass.data[DOMAIN][entry.entry_id]` in `async_unload_entry`. Leaked references prevent garbage collection and can cause state bleed between reloads.

---

## Suggested Build Order

Dependencies flow downward — each layer depends only on layers above it.

```
1. const.py              # No dependencies; needed by everything
2. manifest.json         # Metadata; needed by HA before any Python runs
3. coordinator.py        # Depends on const; contains API client + coordinator
4. config_flow.py        # Depends on const + coordinator (for validation)
5. __init__.py           # Depends on coordinator + config_flow
6. binary_sensor.py      # Depends on coordinator + const
7. sensor.py             # Depends on coordinator + const
8. strings.json + translations/en.json  # Parallel to above; needed by config_flow
9. hacs.json             # Independent; needed only for HACS distribution
```

Build and test in this order:
- Phase 1: const + manifest + coordinator skeleton (unit-testable in isolation)
- Phase 2: config_flow (test with MockConfigEntry and mocked aiohttp)
- Phase 3: __init__ setup/unload (integration test with coordinator)
- Phase 4: binary_sensor + sensor (test entity state from coordinator.data)
- Phase 5: strings + HACS metadata (non-functional, can be done anytime)

---

## Scalability Considerations

| Concern | Small Gatus instance (5 endpoints) | Large instance (100+ endpoints) |
|---------|-----------------------------------|---------------------------------|
| Poll frequency | 60 s default is fine | Same; one HTTP call regardless of entity count |
| Entity count | 4 entities per endpoint = 20 | 400 entities; HA handles this at scale |
| coordinator.data size | Negligible | Still one API response; Gatus paginates via `page` param if needed |
| Multiple Gatus instances | Separate config entries; isolated coordinators | No interference; entry_id scoping prevents conflicts |

For large Gatus instances, `GET /api/v1/endpoints/statuses` returns all endpoints in one call. If Gatus ever paginates, `_async_update_data` would need to loop pages — but that is not a concern for v1.

---

## Sources

- Context7 / official HA developer docs: `/home-assistant/developers.home-assistant`
  - `docs/integration_fetching_data.md` — DataUpdateCoordinator pattern, CoordinatorEntity
  - `docs/config_entries_index.md` — Config entry lifecycle, async_forward_entry_setups
  - `docs/device_registry_index.md` — DeviceInfo, identifiers, device registration
  - `docs/core/integration/config_flow.md` — Config flow, unique_id, Options Flow
  - `docs/creating_integration_manifest.md` — manifest.json fields
  - `docs/core/entity/binary-sensor.md` — BinarySensorEntity, device_class
  - `docs/core/entity.md` — SensorEntityDescription pattern
  - `docs/core/integration-quality-scale/rules/` — entity-unique-id, devices, entity-unavailable, common-modules
