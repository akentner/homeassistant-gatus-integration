"""Tests for GatusDataUpdateCoordinator.

All tests instantiate GatusDataUpdateCoordinator directly.
No test calls hass.config_entries.async_setup() — async_setup_entry
is a NotImplementedError stub until Plan 03.

Error-path tests (4-7) call coordinator._async_update_data() directly inside pytest.raises()
because DataUpdateCoordinator catches UpdateFailed/ConfigEntryAuthFailed internally during
async_refresh() and does NOT re-raise them.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util.dt import utcnow
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.gatus.coordinator import GatusDataUpdateCoordinator

GATUS_URL = "http://gatus.example.com"
STATUSES_URL = f"{GATUS_URL}/api/v1/endpoints/statuses"

# Minimal valid endpoint response
ENDPOINT_A = {
    "key": "core_my-service",
    "name": "my-service",
    "group": "core",
    "results": [
        {
            "success": True,
            "duration": 42_000_000,  # nanoseconds → 42 ms
            "conditionResults": [],
            "timestamp": "2024-01-01T00:00:00Z",
        }
    ],
}

ENDPOINT_SVC_A = {
    "key": "core_svc-a",
    "name": "svc-a",
    "group": "core",
    "results": [
        {
            "success": True,
            "duration": 10_000_000,
            "conditionResults": [],
            "timestamp": "2024-01-01T00:00:00Z",
        }
    ],
}

ENDPOINT_SVC_B = {
    "key": "core_svc-b",
    "name": "svc-b",
    "group": "core",
    "results": [
        {
            "success": True,
            "duration": 20_000_000,
            "conditionResults": [],
            "timestamp": "2024-01-01T00:00:00Z",
        }
    ],
}


async def test_successful_fetch_one_endpoint(hass, aioclient_mock):
    """Test 1 (D-07 case 1): Successful fetch with one endpoint maps data correctly.

    42000000 ns // 1_000_000 == 42 ms.
    """
    aioclient_mock.get(STATUSES_URL, json=[ENDPOINT_A])

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    await coordinator.async_refresh()

    assert coordinator.data is not None
    assert "core_my-service" in coordinator.data
    ep = coordinator.data["core_my-service"]
    assert ep["key"] == "core_my-service"
    assert ep["name"] == "my-service"
    assert ep["group"] == "core"
    assert ep["success"] is True
    assert ep["duration_ms"] == 42
    assert ep["timestamp"] == "2024-01-01T00:00:00Z"
    assert ep["condition_results"] == []


async def test_no_api_key_sends_no_auth_header(hass, aioclient_mock):
    """Test 2 (D-07 case 1b): No api_key — no Authorization header sent."""
    aioclient_mock.get(STATUSES_URL, json=[ENDPOINT_A])

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    await coordinator.async_refresh()

    assert aioclient_mock.call_count == 1
    _method, _url, _data, headers = aioclient_mock.mock_calls[0]
    assert headers is None or "Authorization" not in (headers or {})


async def test_api_key_sends_bearer_header(hass, aioclient_mock):
    """Test 3 (D-07 case 1c): api_key set — Authorization header present."""
    aioclient_mock.get(STATUSES_URL, json=[ENDPOINT_A])

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key="secret", scan_interval=60
    )
    await coordinator.async_refresh()

    assert aioclient_mock.call_count == 1
    _method, _url, _data, headers = aioclient_mock.mock_calls[0]
    assert headers is not None
    assert headers.get("Authorization") == "Bearer secret"


async def test_network_error_raises_update_failed(hass, aioclient_mock):
    """Test 4 (D-07 case 2): Network error → _async_update_data raises UpdateFailed."""
    import aiohttp

    aioclient_mock.get(STATUSES_URL, exc=aiohttp.ClientConnectionError("connection refused"))

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_http_401_raises_config_entry_auth_failed(hass, aioclient_mock):
    """Test 5 (D-07 case 3a): HTTP 401 → ConfigEntryAuthFailed."""
    aioclient_mock.get(STATUSES_URL, status=401)

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_http_403_raises_config_entry_auth_failed(hass, aioclient_mock):
    """Test 6 (D-07 case 3b): HTTP 403 → ConfigEntryAuthFailed."""
    aioclient_mock.get(STATUSES_URL, status=403)

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_invalid_json_raises_update_failed_with_message(hass, aioclient_mock):
    """Test 7: HTTP 200 with invalid JSON → UpdateFailed with 'Invalid JSON' in message."""
    aioclient_mock.get(STATUSES_URL, text="not-json{", status=200)

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    with pytest.raises(UpdateFailed) as exc_info:
        await coordinator._async_update_data()

    assert "Invalid JSON" in str(exc_info.value)


async def test_scheduled_refetch_after_60_seconds(hass, aioclient_mock):
    """Test 8 (Pitfall 6 / success criterion 4): Scheduled re-fetch after 60 s.

    coordinator.async_add_listener() is required to arm the HA polling scheduler.
    The cancel function returned by async_add_listener() must be called in cleanup
    to prevent a lingering timer from causing teardown failures.
    """
    aioclient_mock.get(STATUSES_URL, json=[ENDPOINT_A])

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    # Arm the scheduler — without a listener HA does not schedule polling
    # Save the unsubscribe function so we can cancel the timer after the test
    cancel = coordinator.async_add_listener(lambda: None)
    await coordinator.async_refresh()  # first fetch

    assert aioclient_mock.call_count == 1

    async_fire_time_changed(hass, utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 2
    assert coordinator.data is not None

    # Cancel the listener to stop the polling timer and prevent lingering timers
    cancel()


async def test_parse_endpoint_consecutive_failures(hass, aioclient_mock):
    """Task 1 TDD: consecutive_failures counts leading failures (newest-first).

    Endpoints:
      - ep_a: [fail, fail, pass] → consecutive_failures=2, uptime_pct=33.33...
      - ep_b: [pass, fail]       → consecutive_failures=0, uptime_pct=50.0
      - ep_c: []                 → consecutive_failures=0, uptime_pct=None
    """
    ep_a = {
        "key": "test_ep-a",
        "name": "ep-a",
        "group": "test",
        "results": [
            {"success": False, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:03Z"},
            {"success": False, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:02Z"},
            {"success": True, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:01Z"},
        ],
    }
    ep_b = {
        "key": "test_ep-b",
        "name": "ep-b",
        "group": "test",
        "results": [
            {"success": True, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:02Z"},
            {"success": False, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:01Z"},
        ],
    }
    ep_c = {
        "key": "test_ep-c",
        "name": "ep-c",
        "group": "test",
        "results": [],
    }

    aioclient_mock.get(STATUSES_URL, json=[ep_a, ep_b, ep_c])

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    await coordinator.async_refresh()

    a = coordinator.data["test_ep-a"]
    assert a["consecutive_failures"] == 2
    assert abs(a["uptime_pct"] - (1 / 3 * 100.0)) < 0.01

    b = coordinator.data["test_ep-b"]
    assert b["consecutive_failures"] == 0
    assert b["uptime_pct"] == 50.0

    c = coordinator.data["test_ep-c"]
    assert c["consecutive_failures"] == 0
    assert c["uptime_pct"] is None


async def test_parse_endpoint_uptime_none_when_no_results(hass, aioclient_mock):
    """Task 1 TDD: uptime_pct is None when results list is empty."""
    ep_empty = {
        "key": "test_empty",
        "name": "empty",
        "group": "test",
        "results": [],
    }
    aioclient_mock.get(STATUSES_URL, json=[ep_empty])

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    await coordinator.async_refresh()

    ep = coordinator.data["test_empty"]
    assert ep["uptime_pct"] is None
    assert ep["consecutive_failures"] == 0


async def test_parse_endpoint_all_pass_uptime_100(hass, aioclient_mock):
    """Task 1 TDD: all 3 passing results → uptime_pct=100.0, consecutive_failures=0."""
    ep_all_pass = {
        "key": "test_all-pass",
        "name": "all-pass",
        "group": "test",
        "results": [
            {"success": True, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:01Z"},
            {"success": True, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:02Z"},
            {"success": True, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:03Z"},
        ],
    }
    aioclient_mock.get(STATUSES_URL, json=[ep_all_pass])

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    await coordinator.async_refresh()

    ep = coordinator.data["test_all-pass"]
    assert ep["uptime_pct"] == 100.0
    assert ep["consecutive_failures"] == 0


async def test_parse_endpoint_all_fail_consecutive(hass, aioclient_mock):
    """Task 1 TDD: all 3 failing results → consecutive_failures=3, uptime_pct=0.0."""
    ep_all_fail = {
        "key": "test_all-fail",
        "name": "all-fail",
        "group": "test",
        "results": [
            {"success": False, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:01Z"},
            {"success": False, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:02Z"},
            {"success": False, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:03Z"},
        ],
    }
    aioclient_mock.get(STATUSES_URL, json=[ep_all_fail])

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    await coordinator.async_refresh()

    ep = coordinator.data["test_all-fail"]
    assert ep["consecutive_failures"] == 3
    assert ep["uptime_pct"] == 0.0


async def test_parse_endpoint_uptime_50_pct(hass, aioclient_mock):
    """Task 1 TDD: 2 pass + 2 fail → uptime_pct=50.0."""
    ep_half = {
        "key": "test_half",
        "name": "half",
        "group": "test",
        "results": [
            {"success": True, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:01Z"},
            {"success": True, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:02Z"},
            {"success": False, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:03Z"},
            {"success": False, "duration": 1_000_000, "conditionResults": [], "timestamp": "2024-01-01T00:00:04Z"},
        ],
    }
    aioclient_mock.get(STATUSES_URL, json=[ep_half])

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    await coordinator.async_refresh()

    ep = coordinator.data["test_half"]
    assert ep["uptime_pct"] == 50.0


async def test_disappearing_endpoint_absent_from_data(hass, aioclient_mock):
    """Test 9 (D-02): Endpoint disappears from API — key removed from coordinator.data.

    After second refresh with svc-b absent, coordinator.data must NOT contain 'core_svc-b'.

    AiohttpClientMocker does not consume mocks on match (always returns the first registered
    response for a URL). Use a side_effect counter to return different responses per call.
    """
    import json as _json

    from pytest_homeassistant_custom_component.test_util.aiohttp import (
        AiohttpClientMockResponse,
    )
    from yarl import URL

    call_count = 0
    responses = [
        [ENDPOINT_SVC_A, ENDPOINT_SVC_B],  # first refresh: both endpoints
        [ENDPOINT_SVC_A],  # second refresh: only svc-a
    ]

    async def side_effect(method, url, data):  # type: ignore[no-untyped-def]
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

    coordinator = GatusDataUpdateCoordinator(
        hass, url=GATUS_URL, api_key=None, scan_interval=60
    )
    await coordinator.async_refresh()

    assert "core_svc-a" in coordinator.data
    assert "core_svc-b" in coordinator.data

    await coordinator.async_refresh()

    assert "core_svc-a" in coordinator.data
    assert "core_svc-b" not in coordinator.data
