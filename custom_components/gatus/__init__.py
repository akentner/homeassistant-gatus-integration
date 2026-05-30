"""Gatus integration for Home Assistant.

Phase 2: config_flow.py will be added; MockConfigEntry used in tests bypasses the flow.
Phase 3: async_setup_entry and async_unload_entry will be fully implemented with
          coordinator creation, platform forwarding, and cleanup.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .const import DOMAIN  # noqa: F401 — re-exported; used by HA integration loader

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

type GatusConfigEntry = ConfigEntry[Any]

__all__ = ["DOMAIN", "GatusConfigEntry"]


async def async_setup_entry(hass: HomeAssistant, entry: GatusConfigEntry) -> bool:
    """Set up Gatus from a config entry.

    Not implemented in Phase 1. Coordinator creation and platform forwarding
    will be added in Plan 03 once coordinator.py and sensor.py exist.
    """
    raise NotImplementedError(
        "async_setup_entry is implemented in Plan 03 (coordinator + platform setup)"
    )


async def async_unload_entry(hass: HomeAssistant, entry: GatusConfigEntry) -> bool:
    """Unload a Gatus config entry.

    Not implemented in Phase 1. Platform unloading will be added in Plan 03.
    """
    raise NotImplementedError(
        "async_unload_entry is implemented in Plan 03 (platform teardown)"
    )
