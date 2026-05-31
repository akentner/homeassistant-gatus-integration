"""Binary sensor platform for Gatus endpoint up/down status."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry

from . import GatusConfigEntry
from .const import DEFAULT_PREFIX
from .entity import GatusEntity

PLATFORM_DOMAIN = "binary_sensor"
SENSOR_TYPE = "status"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GatusConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Gatus binary sensors from config entry."""
    coordinator = entry.runtime_data
    prefix = entry.data.get("prefix", DEFAULT_PREFIX)

    entities = [
        GatusBinarySensorEntity(coordinator, entry.entry_id, key, prefix)
        for key in coordinator.data
    ]
    async_add_entities(entities)

    # DEVICE-04: stale entity cleanup on each coordinator update
    entity_registry = async_get_entity_registry(hass)

    @callback
    def _remove_stale_entities() -> None:
        current_keys = set(coordinator.data)
        for entity_entry in list(
            entity_registry.entities.get_entries_for_config_entry_id(entry.entry_id)
        ):
            # Only handle binary_sensor entities from this platform
            if entity_entry.domain != PLATFORM_DOMAIN:
                continue
            # unique_id = {entry_id}_{endpoint_key}_{sensor_type}
            # strip leading {entry_id}_ prefix
            remainder = entity_entry.unique_id[len(entry.entry_id) + 1:]
            endpoint_key = remainder[: -(len(SENSOR_TYPE) + 1)]
            if endpoint_key not in current_keys:
                entity_registry.async_remove(entity_entry.entity_id)

    entry.async_on_unload(
        coordinator.async_add_listener(_remove_stale_entities)
    )


class GatusBinarySensorEntity(GatusEntity, BinarySensorEntity):
    """Connectivity binary sensor for one Gatus endpoint (SENS-01..05)."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator, entry_id, endpoint_key, prefix) -> None:
        super().__init__(
            coordinator,
            entry_id=entry_id,
            endpoint_key=endpoint_key,
            sensor_type=SENSOR_TYPE,
            prefix=prefix,
            platform_domain=PLATFORM_DOMAIN,
        )
        ep = coordinator.data[endpoint_key]
        self._attr_name = ep["name"]

    @property
    def is_on(self) -> bool:
        """True = up; False = down."""
        return self._endpoint["success"]

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return attributes: timestamp, error_reason, duration, failures."""
        ep = self._endpoint
        # SENS-03: first failing condition's condition string, or None if up
        error_reason: str | None = None
        if not ep["success"]:
            for cr in ep["condition_results"]:
                if not cr.get("success", True):
                    error_reason = str(cr.get("condition", ""))
                    break
        return {
            "last_check_timestamp": ep["timestamp"],        # SENS-02
            "error_reason": error_reason,                   # SENS-03
            "response_duration_ms": ep["duration_ms"],      # SENS-04
            "consecutive_failures": ep["consecutive_failures"],  # SENS-05
        }
