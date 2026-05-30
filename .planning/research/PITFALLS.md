# Domain Pitfalls: HA Custom Integration (Polling)

**Domain:** HA custom component — REST polling via DataUpdateCoordinator
**Researched:** 2026-05-30
**Sources:** homeassistant-kroki-integration, homeassistant-chargefinder-integration, phone-logger-integration (sibling integrations on same HA host), HA developer docs

---

## Critical Pitfalls

### P1: Own aiohttp.ClientSession Instead of async_get_clientsession

**Warning sign:** `aiohttp.ClientSession()` anywhere in custom component code.

**Consequence:** Resource leak; misses HA's SSL context/proxy support; complicates testing.

**Prevention:** Use `async_get_clientsession(hass)` everywhere — in coordinator, in config_flow for validation. No cleanup needed.

**Phase:** Core scaffold.

---

### P2: Unique ID From Mutable Data

**Warning sign:** Unique ID contains endpoint name/group string from Gatus without `entry_id` prefix.

**Consequence:** User renames Gatus endpoint → key changes → old entity orphaned (4 entities per endpoint). Automations silently break.

**Prevention:** Format: `f"{config_entry.entry_id}_{endpoint_key}_{sensor_type}"`. Document that renaming a Gatus endpoint requires manual entity cleanup.

**Phase:** Sensor entity setup.

---

### P3: Entities Not Removed When Gatus Endpoints Disappear

**Warning sign:** `async_add_entities` called once at setup with no reconciliation.

**Consequence:** Permanently "unavailable" entities in dashboard when Gatus endpoint deleted.

**Prevention:** On coordinator update, compare new endpoint keys against registered entities. Use `entity_registry.async_remove(entity_id)` for stale entries. Maintain endpoint_key → entity_id mapping at runtime.

**Phase:** Sensor entity setup. Most architecturally complex requirement.

---

### P4: Blocking I/O in Event Loop

**Warning sign:** `import requests`, `time.sleep`, or sync context managers on async resources.

**Consequence:** HA detects and logs blocking calls (since 2024.x); integration may be disabled; other integrations freeze.

**Prevention:** `aiohttp` only. Use `async with session.get(...)`. Never `requests`, `urllib`, `time.sleep`.

**Phase:** Core scaffold.

---

### P5: Missing/Malformed strings.json / translations/en.json

**Warning sign:** UI shows raw dotted keys. `hassfest` fails on translation check.

**Prevention:** Create `strings.json` and `translations/en.json` together **before** writing `config_flow.py`. Cover: `user` step, `cannot_connect` error, `already_configured` abort, options `init` step with interval field.

**Phase:** Config flow setup (create strings first).

---

### P6: Deprecated async_forward_entry_setup (Singular)

**Warning sign:** `async_forward_entry_setup(entry, "sensor")` called once per platform.

**Prevention:** Always `async_forward_entry_setups(entry, PLATFORMS)` (plural, list). Mirror with `async_unload_platforms(entry, PLATFORMS)`.

**Phase:** Core scaffold.

---

### P7: Missing/Incomplete async_unload_entry

**Warning sign:** No `async_unload_entry` or it doesn't pop `entry.entry_id` from `hass.data[DOMAIN]`.

**Consequence:** Reloading leaves stale coordinator polling alongside new one. Options changes have no effect.

**Prevention:**
```python
async def async_unload_entry(hass, entry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
```

**Phase:** Core scaffold (implement before anything else).

---

### P8: async_config_entry_first_refresh Not Called

**Warning sign:** Coordinator constructed, then `async_forward_entry_setups` called without first refresh.

**Consequence:** `coordinator.data = None`. Entity property accessors crash.

**Prevention:** Always `await coordinator.async_config_entry_first_refresh()` after constructing coordinator, before platform setup. Raises `ConfigEntryNotReady` automatically on failure.

**Phase:** Core scaffold.

---

## Moderate Pitfalls

### P9: Missing HA Version in hacs.json

**Prevention:** Always include `"homeassistant": "2024.7.0"` (ensures plural setup API available).

### P10: manifest.json Missing version Field

**Prevention:** Include `"version": "0.1.0"` from day one. `hassfest` rejects without it.

### P11: Config Entry VERSION Not Declared

**Prevention:** Declare `VERSION = 1` in config flow. For any schema change: implement `async_migrate_entry`, bump VERSION.

### P12: No Duplicate Entry Guard

**Prevention:** In `async_step_user`: `await self.async_set_unique_id(normalized_url)` + `self._abort_if_unique_id_configured()`. Normalize URL (strip trailing slash). Add `"already_configured"` to strings.json aborts.

### P13: available Returns True When Coordinator Failed

**Prevention:** Inherit from `CoordinatorEntity`. Do not override `available` independently of `coordinator.last_update_success`.

---

## Minor Pitfalls

### P14: Gatus Duration Is Nanoseconds, Not Milliseconds

Gatus returns Go `time.Duration` as nanoseconds. `42000000` = 42ms.

**Prevention:** Divide raw `duration` by 1,000,000. Use `SensorDeviceClass.DURATION` + `UnitOfTime.MILLISECONDS`.

**Phase:** Sensor entity setup.

### P15: suggested_object_id Not Set

**Prevention:** Override `suggested_object_id` property: `f"gatus_{endpoint_key}_{sensor_type}"`. Prevents UUID-based entity IDs.

### P16: _attr_has_entity_name Not Set

**Prevention:** `_attr_has_entity_name = True` on all entity classes. HA composes "Device Name — Sensor Suffix" automatically.

---

## Phase Mapping Summary

| Phase | Critical Pitfalls |
|-------|-------------------|
| Core scaffold | P1 (session), P4 (blocking), P6 (plural setup), P7 (unload), P8 (first_refresh) |
| Config flow | P5 (strings), P11 (VERSION), P12 (duplicate guard) |
| Sensor entity setup | P2 (unique ID), P3 (entity removal), P13 (available), P14 (duration units), P15, P16 |
| HACS packaging | P9 (hacs.json), P10 (manifest version) |
