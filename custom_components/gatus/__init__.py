"""Gatus integration for Home Assistant.

Implements the config entry lifecycle:
  - async_setup_entry: creates GatusDataUpdateCoordinator, calls
    async_config_entry_first_refresh, stores coordinator in entry.runtime_data.
  - async_unload_entry: returns True; HA clears entry.runtime_data automatically.

Phase 1: no platform forwarding (no entities yet). Sensor/binary_sensor
forwarding will be added in Phase 3.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DEFAULT_SCAN_INTERVAL
from .coordinator import GatusDataUpdateCoordinator

type GatusConfigEntry = ConfigEntry[GatusDataUpdateCoordinator]

__all__ = ["GatusConfigEntry", "async_setup_entry", "async_unload_entry"]


async def async_setup_entry(hass: HomeAssistant, entry: GatusConfigEntry) -> bool:
    """Set up Gatus from a config entry.

    Creates the coordinator, performs the first refresh, then stores the
    coordinator in entry.runtime_data. runtime_data is ONLY assigned after
    the first refresh succeeds (Pitfall 5 prevention — T-03-01).

    Error handling:
      - UpdateFailed raised from _async_update_data is auto-converted to
        ConfigEntryNotReady by async_config_entry_first_refresh.
      - ConfigEntryAuthFailed propagates unchanged → HA triggers reauth flow.
      - Do NOT wrap async_config_entry_first_refresh in try/except.
    """
    coordinator = GatusDataUpdateCoordinator(
        hass,
        url=entry.data["url"],
        api_key=entry.data.get("api_key"),
        scan_interval=entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL),
    )

    # auto-converts UpdateFailed → ConfigEntryNotReady on failure (D-04)
    # ConfigEntryAuthFailed propagates as-is (D-03)
    await coordinator.async_config_entry_first_refresh()

    # Only assign runtime_data after a successful first refresh (T-03-01 / Pitfall 5)
    entry.runtime_data = coordinator

    # Phase 1: no platforms; async_forward_entry_setups added in Phase 3
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GatusConfigEntry) -> bool:
    """Unload a Gatus config entry.

    Phase 1: no platforms to unload. HA clears entry.runtime_data automatically
    after this function returns True.
    """
    # Phase 1: nothing to unload; platform unloading added in Phase 3
    return True
