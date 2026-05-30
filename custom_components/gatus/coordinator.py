"""Gatus DataUpdateCoordinator — single polling point for all endpoint data.

Fetches GET /api/v1/endpoints/statuses once per scan_interval.
Error classification:
  - 401/403 → ConfigEntryAuthFailed (triggers re-auth flow)
  - Any other HTTP error or network exception → UpdateFailed
  - Unparseable JSON → UpdateFailed("Invalid JSON from Gatus: ...")

The ConfigEntryNotReady conversion for first-refresh failures is handled by
async_config_entry_first_refresh() in __init__.py (Plan 03). This module
never raises ConfigEntryNotReady directly.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import TypedDict

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class GatusEndpoint(TypedDict):
    """Typed representation of a single Gatus endpoint from the API response."""

    key: str  # raw Gatus endpoint key, e.g. "core_my-service"
    name: str  # human-readable name
    group: str  # Gatus group name
    success: bool  # latest result success flag
    duration_ms: int  # latest result duration in ms (Gatus nanoseconds // 1_000_000)
    timestamp: str  # ISO 8601 timestamp of latest result
    condition_results: list[dict[str, object]]  # raw conditionResults from latest result


class GatusDataUpdateCoordinator(DataUpdateCoordinator[dict[str, GatusEndpoint]]):
    """Coordinator that polls Gatus /api/v1/endpoints/statuses and shapes results.

    One instance per config entry. All sensor entities share this coordinator.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        url: str,
        api_key: str | None,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialize coordinator.

        Args:
            hass: Home Assistant instance.
            url: Base URL of the Gatus instance (trailing slash stripped).
            api_key: Optional Bearer token for Gatus authentication.
            scan_interval: Polling interval in seconds.
        """
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self._url = url.rstrip("/")
        self._api_key = api_key

    async def _async_update_data(self) -> dict[str, GatusEndpoint]:
        """Fetch all endpoint statuses from Gatus API.

        Returns a fresh dict keyed by endpoint_key. Endpoints absent from the
        API response are not included, implementing D-02 (disappearing endpoints).

        Raises:
            ConfigEntryAuthFailed: On HTTP 401 or 403.
            UpdateFailed: On any other HTTP error, network error, or JSON parse failure.
        """
        statuses_url = f"{self._url}/api/v1/endpoints/statuses"

        # Only set Authorization header if api_key is truthy — never log the value
        headers: dict[str, str] | None = None
        if self._api_key:
            headers = {"Authorization": f"Bearer {self._api_key}"}

        session = async_get_clientsession(self.hass)

        try:
            async with asyncio.timeout(10):
                resp = await session.get(statuses_url, headers=headers)
        except Exception as err:
            raise UpdateFailed(f"Error communicating with Gatus API: {err}") from err

        if resp.status in (401, 403):
            raise ConfigEntryAuthFailed(
                f"Authentication failed (HTTP {resp.status})"
            )

        if resp.status != 200:
            raise UpdateFailed(f"Unexpected HTTP {resp.status} from Gatus API")

        try:
            raw_list: list[dict[str, object]] = await resp.json(content_type=None)
        except (ValueError, Exception) as err:
            raise UpdateFailed(f"Invalid JSON from Gatus: {err}") from err

        if not isinstance(raw_list, list):
            raise UpdateFailed(
                f"Invalid JSON from Gatus: expected a list, got {type(raw_list).__name__}"
            )

        return {str(ep["key"]): _parse_endpoint(ep) for ep in raw_list}


def _parse_endpoint(raw: dict[str, object]) -> GatusEndpoint:
    """Extract and shape a single endpoint dict from the Gatus API response.

    If the endpoint has no results, defaults are used (0/False/"").
    """
    results_raw = raw.get("results")
    results: list[dict[str, object]] = results_raw if isinstance(results_raw, list) else []
    latest: dict[str, object] = results[0] if results else {}

    duration_raw = latest.get("duration", 0)
    duration_ns: int = duration_raw if isinstance(duration_raw, int) else 0

    condition_raw = latest.get("conditionResults")
    condition_results: list[dict[str, object]] = condition_raw if isinstance(condition_raw, list) else []

    return GatusEndpoint(
        key=str(raw.get("key", "")),
        name=str(raw.get("name", "")),
        group=str(raw.get("group", "")),
        success=bool(latest.get("success", False)),
        duration_ms=duration_ns // 1_000_000,
        timestamp=str(latest.get("timestamp", "")),
        condition_results=condition_results,
    )
