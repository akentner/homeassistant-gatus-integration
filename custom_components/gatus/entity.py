"""Shared base entity for all Gatus sensor platforms."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import GatusDataUpdateCoordinator, GatusEndpoint


class GatusEntity(CoordinatorEntity[GatusDataUpdateCoordinator]):
    """Base entity for Gatus endpoint sensors.

    Handles: unique_id, availability, DeviceInfo, and the _endpoint accessor.
    Subclasses provide: platform-specific entity_id, state, attributes.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: GatusDataUpdateCoordinator,
        entry_id: str,
        endpoint_key: str,
        sensor_type: str,
        prefix: str,
        platform_domain: str,
    ) -> None:
        """Initialize base entity.

        Args:
            coordinator: The shared GatusDataUpdateCoordinator.
            entry_id: config_entry.entry_id for unique_id and device identifiers.
            endpoint_key: Gatus endpoint key (e.g. "core_my-service").
            sensor_type: Short type label (e.g. "status", "response_time",
                         "uptime", "conditions").
            prefix: Entity object ID prefix from entry.data["prefix"].
            platform_domain: "binary_sensor" or "sensor".
        """
        super().__init__(coordinator)
        self._endpoint_key = endpoint_key
        self._sensor_type = sensor_type

        # DEVICE-02: unique_id = {entry_id}_{endpoint_key}_{sensor_type}
        self._attr_unique_id = f"{entry_id}_{endpoint_key}_{sensor_type}"

        # DEVICE-03: entity_id = {platform_domain}.{prefix}{endpoint_key}_{sensor_type}
        self.entity_id = f"{platform_domain}.{prefix}{endpoint_key}_{sensor_type}"

        # DEVICE-01: group endpoints under one HA Device per Gatus group
        group = coordinator.data[endpoint_key]["group"]
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{group}")},
            name=group,
            manufacturer="Gatus",
        )

    @property
    def available(self) -> bool:
        """Entity unavailable if coordinator has no data or key missing."""
        return (
            super().available
            and self.coordinator.data is not None
            and self._endpoint_key in self.coordinator.data
        )

    @property
    def _endpoint(self) -> GatusEndpoint:
        """Convenience accessor for this entity's endpoint data."""
        return self.coordinator.data[self._endpoint_key]
