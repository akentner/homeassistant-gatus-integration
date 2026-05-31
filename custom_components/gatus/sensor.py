"""Sensor platform for Gatus endpoint metrics."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from . import GatusConfigEntry
from .const import DEFAULT_PREFIX
from .entity import GatusEntity

PLATFORM_DOMAIN = "sensor"
SENSOR_TYPE_RESPONSE = "response_time"
SENSOR_TYPE_UPTIME = "uptime"
SENSOR_TYPE_CONDITIONS = "conditions"
_SENSOR_TYPES = (SENSOR_TYPE_RESPONSE, SENSOR_TYPE_UPTIME, SENSOR_TYPE_CONDITIONS)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GatusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gatus sensors from config entry."""
    coordinator = entry.runtime_data
    prefix = entry.data.get("prefix", DEFAULT_PREFIX)

    entities: list[GatusEntity] = []
    for key in coordinator.data:
        entities.append(GatusResponseTimeSensor(coordinator, entry.entry_id, key, prefix))
        entities.append(GatusUptimeSensor(coordinator, entry.entry_id, key, prefix))
        entities.append(GatusConditionsSensor(coordinator, entry.entry_id, key, prefix))
    async_add_entities(entities)

    # DEVICE-04: stale entity cleanup on each coordinator update
    entity_registry = async_get_entity_registry(hass)

    @callback
    def _remove_stale_entities() -> None:
        current_keys = set(coordinator.data)
        for entity_entry in list(
            entity_registry.entities.get_entries_for_config_entry_id(entry.entry_id)
        ):
            if entity_entry.domain != PLATFORM_DOMAIN:
                continue
            # unique_id = {entry_id}_{endpoint_key}_{sensor_type}
            # determine sensor_type suffix to strip
            uid = entity_entry.unique_id
            stripped = uid[len(entry.entry_id) + 1:]  # remove "{entry_id}_"
            endpoint_key = None
            for stype in _SENSOR_TYPES:
                if stripped.endswith(f"_{stype}"):
                    endpoint_key = stripped[: -(len(stype) + 1)]
                    break
            if endpoint_key is not None and endpoint_key not in current_keys:
                entity_registry.async_remove(entity_entry.entity_id)

    entry.async_on_unload(
        coordinator.async_add_listener(_remove_stale_entities)
    )


class GatusResponseTimeSensor(GatusEntity, SensorEntity):
    """Response time in ms for one Gatus endpoint (SENS-06)."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = "ms"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry_id, endpoint_key, prefix) -> None:
        super().__init__(
            coordinator,
            entry_id=entry_id,
            endpoint_key=endpoint_key,
            sensor_type=SENSOR_TYPE_RESPONSE,
            prefix=prefix,
            platform_domain=PLATFORM_DOMAIN,
        )
        self._attr_name = f"{coordinator.data[endpoint_key]['name']} Response Time"

    @property
    def native_value(self) -> int:
        return self._endpoint["duration_ms"]


class GatusUptimeSensor(GatusEntity, SensorEntity):
    """Uptime percentage for one Gatus endpoint (SENS-07)."""

    _attr_native_unit_of_measurement = "%"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator, entry_id, endpoint_key, prefix) -> None:
        super().__init__(
            coordinator,
            entry_id=entry_id,
            endpoint_key=endpoint_key,
            sensor_type=SENSOR_TYPE_UPTIME,
            prefix=prefix,
            platform_domain=PLATFORM_DOMAIN,
        )
        self._attr_name = f"{coordinator.data[endpoint_key]['name']} Uptime"

    @property
    def native_value(self) -> float | None:
        """Returns None when no results (entity becomes unavailable per D-03)."""
        return self._endpoint["uptime_pct"]


class GatusConditionsSensor(GatusEntity, SensorEntity):
    """Conditions pass/total string for one Gatus endpoint (SENS-08)."""

    def __init__(self, coordinator, entry_id, endpoint_key, prefix) -> None:
        super().__init__(
            coordinator,
            entry_id=entry_id,
            endpoint_key=endpoint_key,
            sensor_type=SENSOR_TYPE_CONDITIONS,
            prefix=prefix,
            platform_domain=PLATFORM_DOMAIN,
        )
        self._attr_name = f"{coordinator.data[endpoint_key]['name']} Conditions"

    @property
    def native_value(self) -> str:
        """Return 'X/Y' — passed_conditions/total_conditions."""
        crs = self._endpoint["condition_results"]
        total = len(crs)
        passed = sum(1 for cr in crs if cr.get("success", False))
        return f"{passed}/{total}"

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        return {
            "condition_details": [
                {"condition": cr.get("condition", ""), "success": bool(cr.get("success", False))}
                for cr in self._endpoint["condition_results"]
            ]
        }
