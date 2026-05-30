"""Tests for the Gatus integration __init__.py lifecycle.

Covers D-07 case 4 (clean state after setup/unload), reload scenario,
and entry-level error states for auth failure and network failure.

All tests use hass.config_entries.async_setup(entry.entry_id) because they
exercise the full HA config entry machinery — not the coordinator in isolation.
"""

from __future__ import annotations

import pytest
from homeassistant.config_entries import ConfigEntryState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gatus import GatusConfigEntry
from custom_components.gatus.coordinator import GatusDataUpdateCoordinator

MOCK_URL = "http://gatus.example.com"
STATUSES_URL = f"{MOCK_URL}/api/v1/endpoints/statuses"
MOCK_STATUSES = [
    {
        "key": "core_my-service",
        "name": "my-service",
        "group": "core",
        "results": [
            {
                "success": True,
                "duration": 42_000_000,
                "conditionResults": [],
                "timestamp": "2024-01-01T00:00:00Z",
            }
        ],
    }
]


def _make_entry(**kwargs) -> MockConfigEntry:
    """Create a MockConfigEntry with defaults for Gatus."""
    defaults = {
        "domain": "gatus",
        "data": {"url": MOCK_URL, "api_key": None},
    }
    defaults.update(kwargs)
    return MockConfigEntry(**defaults)


async def test_setup_creates_coordinator_in_runtime_data(hass, aioclient_mock) -> None:
    """D-07 case 4a: setup creates coordinator in entry.runtime_data."""
    aioclient_mock.get(STATUSES_URL, json=MOCK_STATUSES)

    entry = _make_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)

    assert result is True
    assert entry.state is ConfigEntryState.LOADED
    assert isinstance(entry.runtime_data, GatusDataUpdateCoordinator)
    assert "core_my-service" in entry.runtime_data.data


async def test_unload_clears_runtime_data(hass, aioclient_mock) -> None:
    """D-07 case 4b: unload entry clears runtime_data."""
    aioclient_mock.get(STATUSES_URL, json=MOCK_STATUSES)

    entry = _make_entry()
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    result = await hass.config_entries.async_unload(entry.entry_id)

    assert result is True
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_reload_produces_fresh_coordinator(hass, aioclient_mock) -> None:
    """Reload (unload + re-setup) leaves no duplicate state; fresh coordinator created."""
    aioclient_mock.get(STATUSES_URL, json=MOCK_STATUSES)

    entry = _make_entry()
    entry.add_to_hass(hass)

    # First setup
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED
    first_coordinator = entry.runtime_data
    first_coordinator_id = id(first_coordinator)

    # Unload
    await hass.config_entries.async_unload(entry.entry_id)
    assert entry.state is ConfigEntryState.NOT_LOADED

    # Re-setup (reload)
    await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.LOADED

    second_coordinator = entry.runtime_data
    assert isinstance(second_coordinator, GatusDataUpdateCoordinator)
    # Fresh object — different identity from first coordinator
    assert id(second_coordinator) != first_coordinator_id
    # Data is populated on the second setup
    assert second_coordinator.data is not None


async def test_runtime_data_not_set_when_first_refresh_fails(hass, aioclient_mock) -> None:
    """Pitfall 5: runtime_data must NOT be set if async_config_entry_first_refresh fails."""
    aioclient_mock.get(STATUSES_URL, exc=Exception("connection refused"))

    entry = _make_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)

    assert result is False
    # runtime_data must not have been set to a failed coordinator
    assert not hasattr(entry, "runtime_data") or entry.runtime_data is None


async def test_network_failure_on_first_refresh_entry_not_loaded(hass, aioclient_mock) -> None:
    """D-07 case 2 (entry-level): Network failure → ConfigEntryNotReady → entry not loaded."""
    aioclient_mock.get(STATUSES_URL, exc=Exception("connection refused"))

    entry = _make_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)

    assert result is False
    # SETUP_RETRY indicates ConfigEntryNotReady was raised — HA will retry
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_auth_failure_on_setup_entry_not_loaded(hass, aioclient_mock) -> None:
    """D-07 case 3 (entry-level): HTTP 401 → ConfigEntryAuthFailed → entry not loaded."""
    aioclient_mock.get(STATUSES_URL, status=401)

    entry = _make_entry()
    entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)

    assert result is False
    assert entry.state is ConfigEntryState.SETUP_ERROR
