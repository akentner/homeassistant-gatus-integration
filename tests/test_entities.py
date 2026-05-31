"""Integration tests for Gatus entity loading, attributes, and stale cleanup.

Covers SENS-01..08 and DEVICE-01..04 via the full HA config entry machinery.

The top-level import from custom_components.gatus is required to ensure Python
caches our project's custom_components namespace package in sys.modules before
HA's loader runs _async_mount_config_dir (which temporarily puts the testing
config dir in sys.path, which would otherwise shadow our custom_components).
"""

from __future__ import annotations

import json as _json

# This import forces our custom_components namespace package into sys.modules
# before the hass fixture's _async_mount_config_dir can shadow it.
from custom_components.gatus.coordinator import GatusDataUpdateCoordinator  # noqa: F401
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMockResponse,
)
from yarl import URL

GATUS_URL = "http://gatus.example.com"
STATUSES_URL = f"{GATUS_URL}/api/v1/endpoints/statuses"

ENDPOINT_A_RESPONSE = [
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

ENDPOINT_A_DOWN_RESPONSE = [
    {
        "key": "core_my-service",
        "name": "my-service",
        "group": "core",
        "results": [
            {
                "success": False,
                "duration": 99_000_000,
                "conditionResults": [
                    {"condition": "[STATUS] == 200", "success": False},
                    {"condition": "[BODY] contains 'ok'", "success": True},
                ],
                "timestamp": "2024-01-01T00:01:00Z",
            }
        ],
    }
]

ENDPOINT_A_NO_RESULTS = [
    {
        "key": "core_my-service",
        "name": "my-service",
        "group": "core",
        "results": [],
    }
]

TWO_GROUP_RESPONSE = [
    {
        "key": "core_service-a",
        "name": "service-a",
        "group": "core",
        "results": [{"success": True, "duration": 10_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:00Z"}],
    },
    {
        "key": "core_service-b",
        "name": "service-b",
        "group": "core",
        "results": [{"success": False, "duration": 5_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:00Z"}],
    },
    {
        "key": "edge_proxy",
        "name": "proxy",
        "group": "edge",
        "results": [{"success": True, "duration": 3_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:00Z"}],
    },
]


async def _setup_integration(hass, aioclient_mock, response=ENDPOINT_A_RESPONSE):
    """Set up the Gatus integration with a mocked HTTP response."""
    aioclient_mock.get(STATUSES_URL, json=response)
    entry = MockConfigEntry(
        domain="gatus",
        data={"url": GATUS_URL, "api_key": None, "prefix": "gatus_"},
        options={},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


# ---------------------------------------------------------------------------
# Test 1: binary sensor created and state "on" when endpoint is up (SENS-01)
# ---------------------------------------------------------------------------
async def test_binary_sensor_state_up(hass, aioclient_mock) -> None:
    """SENS-01: Binary sensor created with state 'on' when endpoint success=True."""
    await _setup_integration(hass, aioclient_mock)

    state = hass.states.get("binary_sensor.gatus_core_my_service_status")
    assert state is not None
    assert state.state == "on"


# ---------------------------------------------------------------------------
# Test 2: binary sensor attributes (SENS-02..05)
# ---------------------------------------------------------------------------
async def test_binary_sensor_attributes(hass, aioclient_mock) -> None:
    """SENS-02..05: All 4 required attribute keys present; error_reason is None when up."""
    await _setup_integration(hass, aioclient_mock)

    state = hass.states.get("binary_sensor.gatus_core_my_service_status")
    assert state is not None
    attrs = state.attributes

    assert "last_check_timestamp" in attrs         # SENS-02
    assert attrs["last_check_timestamp"] == "2024-01-01T00:00:00Z"
    assert "error_reason" in attrs                 # SENS-03
    assert attrs["error_reason"] is None           # None when up
    assert "response_duration_ms" in attrs         # SENS-04
    assert attrs["response_duration_ms"] == 42
    assert "consecutive_failures" in attrs         # SENS-05
    assert attrs["consecutive_failures"] == 0


# ---------------------------------------------------------------------------
# Test 3: binary sensor state "off" and error_reason set when endpoint is down
# ---------------------------------------------------------------------------
async def test_binary_sensor_state_down(hass, aioclient_mock) -> None:
    """SENS-01/SENS-03: State 'off' and error_reason set to first failing condition."""
    await _setup_integration(hass, aioclient_mock, response=ENDPOINT_A_DOWN_RESPONSE)

    state = hass.states.get("binary_sensor.gatus_core_my_service_status")
    assert state is not None
    assert state.state == "off"
    assert state.attributes["error_reason"] == "[STATUS] == 200"


# ---------------------------------------------------------------------------
# Test 4: response time sensor (SENS-06)
# ---------------------------------------------------------------------------
async def test_response_time_sensor(hass, aioclient_mock) -> None:
    """SENS-06: Response time sensor state equals duration_ms value."""
    await _setup_integration(hass, aioclient_mock)

    state = hass.states.get("sensor.gatus_core_my_service_response_time")
    assert state is not None
    # HA stores numeric sensor state as a string
    assert state.state == "42"


# ---------------------------------------------------------------------------
# Test 5: uptime sensor unavailable when no results (SENS-07)
# ---------------------------------------------------------------------------
async def test_uptime_sensor_none_when_no_results(hass, aioclient_mock) -> None:
    """SENS-07: Uptime sensor is unavailable when endpoint has no results."""
    await _setup_integration(hass, aioclient_mock, response=ENDPOINT_A_NO_RESULTS)

    state = hass.states.get("sensor.gatus_core_my_service_uptime")
    assert state is not None
    # native_value=None → HA reports state as "unknown"
    assert state.state == "unknown"


# ---------------------------------------------------------------------------
# Test 7: stale entity removed when endpoint disappears (DEVICE-04)
# ---------------------------------------------------------------------------
async def test_stale_entity_removed(hass, aioclient_mock) -> None:
    """DEVICE-04: After coordinator refreshes with endpoint absent, entity removed from registry."""
    from datetime import timedelta

    endpoint_b_response = [
        {
            "key": "core_my-service",
            "name": "my-service",
            "group": "core",
            "results": [
                {
                    "success": True,
                    "duration": 10_000_000,
                    "conditionResults": [],
                    "timestamp": "2024-01-01T00:00:00Z",
                }
            ],
        },
        {
            "key": "core_other-service",
            "name": "other-service",
            "group": "core",
            "results": [
                {
                    "success": True,
                    "duration": 5_000_000,
                    "conditionResults": [],
                    "timestamp": "2024-01-01T00:00:00Z",
                }
            ],
        },
    ]

    call_count = 0
    responses = [
        endpoint_b_response,   # first refresh: two endpoints
        ENDPOINT_A_RESPONSE,   # second refresh: only my-service
    ]

    async def side_effect(method, url, data):
        nonlocal call_count
        body = responses[min(call_count, len(responses) - 1)]
        call_count += 1
        return AiohttpClientMockResponse(
            method=method,
            url=URL(STATUSES_URL),
            status=200,
            text=_json.dumps(body),
        )

    aioclient_mock.get(STATUSES_URL, side_effect=side_effect)

    entry = MockConfigEntry(
        domain="gatus",
        data={"url": GATUS_URL, "api_key": None, "prefix": "gatus_"},
        options={},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Verify both entities exist after initial load
    er = async_get_entity_registry(hass)
    assert er.async_get("binary_sensor.gatus_core_my_service_status") is not None
    assert er.async_get("binary_sensor.gatus_core_other_service_status") is not None

    # Fire time change to trigger second coordinator poll
    async_fire_time_changed(hass, utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()

    # other-service should be removed; my-service should remain
    assert er.async_get("binary_sensor.gatus_core_my_service_status") is not None
    assert er.async_get("binary_sensor.gatus_core_other_service_status") is None


# ---------------------------------------------------------------------------
# Test 8: group binary sensor ON when all endpoints up
# ---------------------------------------------------------------------------
async def test_group_binary_sensor_all_up(hass, aioclient_mock) -> None:
    """Group sensor is ON when all endpoints in group are up."""
    await _setup_integration(hass, aioclient_mock)  # single endpoint, up
    state = hass.states.get("binary_sensor.gatus_core_group")
    assert state is not None
    assert state.state == "on"
    assert state.attributes["green_endpoints"] == ["my-service"]
    assert state.attributes["red_endpoints"] == []


# ---------------------------------------------------------------------------
# Test 9: group binary sensor OFF when any endpoint down
# ---------------------------------------------------------------------------
async def test_group_binary_sensor_any_down(hass, aioclient_mock) -> None:
    """Group sensor is OFF when any endpoint in group is down."""
    await _setup_integration(hass, aioclient_mock, response=TWO_GROUP_RESPONSE)
    state = hass.states.get("binary_sensor.gatus_core_group")
    assert state is not None
    assert state.state == "off"
    attrs = state.attributes
    assert "service-a" in attrs["green_endpoints"]
    assert "service-b" in attrs["red_endpoints"]


# ---------------------------------------------------------------------------
# Test 10: one group sensor per unique group
# ---------------------------------------------------------------------------
async def test_group_binary_sensor_multiple_groups(hass, aioclient_mock) -> None:
    """One group sensor created per unique group."""
    await _setup_integration(hass, aioclient_mock, response=TWO_GROUP_RESPONSE)
    core_state = hass.states.get("binary_sensor.gatus_core_group")
    edge_state = hass.states.get("binary_sensor.gatus_edge_group")
    assert core_state is not None
    assert edge_state is not None
    assert edge_state.state == "on"
    assert edge_state.attributes["green_endpoints"] == ["proxy"]


# ---------------------------------------------------------------------------
# Test 11: conditions sensor no longer exists
# ---------------------------------------------------------------------------
async def test_no_conditions_sensor(hass, aioclient_mock) -> None:
    """Conditions sensor entity must not be created."""
    await _setup_integration(hass, aioclient_mock)
    state = hass.states.get("sensor.gatus_core_my_service_conditions")
    assert state is None
