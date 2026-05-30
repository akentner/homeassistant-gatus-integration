"""Config flow for the Gatus integration.

Implements:
  - GatusConfigFlow.async_step_user: URL + API key + prefix form with validation
  - _validate_gatus_connection: shared helper reused in Reconfigure and Reauth flows
"""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DEFAULT_PREFIX, DEFAULT_SCAN_INTERVAL, DOMAIN


class CannotConnect(Exception):
    """Raised when the Gatus instance is unreachable or returns a non-auth error."""


class InvalidAuth(Exception):
    """Raised when the Gatus instance returns 401 or 403."""


async def _validate_gatus_connection(
    session: aiohttp.ClientSession,
    url: str,
    api_key: str | None,
) -> None:
    """Validate connectivity to a Gatus instance.

    Raises:
        CannotConnect: if the URL is unreachable or returns an unexpected error.
        InvalidAuth: if the server returns 401 or 403.
    """
    headers: dict[str, str] = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        async with asyncio.timeout(10):
            resp = await session.get(
                f"{url}/api/v1/endpoints/statuses",
                headers=headers,
            )
    except aiohttp.ClientError as exc:
        raise CannotConnect from exc

    if resp.status in (401, 403):
        raise InvalidAuth
    if not resp.ok:
        raise CannotConnect


_STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("url"): selector.TextSelector(),
        vol.Optional("api_key", default=""): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
        vol.Optional("prefix", default=DEFAULT_PREFIX): selector.TextSelector(),
    }
)


class GatusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gatus."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Normalize URL
            url: str = user_input["url"].rstrip("/")

            # Normalize API key — treat empty string as None
            api_key: str | None = user_input.get("api_key") or None

            # Apply prefix default
            prefix: str = user_input.get("prefix") or DEFAULT_PREFIX

            try:
                await _validate_gatus_connection(async_get_clientsession(self.hass), url, api_key)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                # Duplicate check — use lowercased URL as unique ID
                await self.async_set_unique_id(url.lower())
                self._abort_if_unique_id_configured()

                # Title is the hostname
                title = urlparse(url).hostname or url

                return self.async_create_entry(
                    title=title,
                    data={"url": url, "api_key": api_key, "prefix": prefix},
                    options={"scan_interval": DEFAULT_SCAN_INTERVAL},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle re-authentication — implemented in Phase 2 Plan 02."""
        return self.async_abort(reason="reauth_not_implemented")
