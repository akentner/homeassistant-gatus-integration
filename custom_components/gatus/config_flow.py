"""Config flow for the Gatus integration.

Implements:
  - GatusConfigFlow.async_step_user: URL + API key + prefix form with validation
  - GatusConfigFlow.async_step_reauth / async_step_reauth_confirm: API key rotation on 401
  - GatusConfigFlow.async_step_reconfigure: in-place URL + API key change
  - OptionsFlowHandler.async_step_init: scan interval + API key rotation post-setup
  - _validate_gatus_connection: shared helper reused by all flows that need validation
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import DEFAULT_PREFIX, DEFAULT_SCAN_INTERVAL, DOMAIN, MAX_SCAN_INTERVAL, MIN_SCAN_INTERVAL


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


class OptionsFlowHandler(OptionsFlow):
    """Handle an options flow for Gatus."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the options form."""
        errors: dict[str, str] = {}

        current_interval = self.config_entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
        current_key = (
            self.config_entry.options.get("api_key")
            or self.config_entry.data.get("api_key")
            or ""
        )

        if user_input is not None:
            scan_interval = int(user_input.get("scan_interval", current_interval))

            if not MIN_SCAN_INTERVAL <= scan_interval <= MAX_SCAN_INTERVAL:
                errors["scan_interval"] = "scan_interval_out_of_range"
            else:
                api_key: str | None = user_input.get("api_key") or None

                # Update coordinator interval live without requiring a reload
                self.config_entry.runtime_data.update_interval = timedelta(seconds=scan_interval)

                return self.async_create_entry(
                    data={"scan_interval": scan_interval, "api_key": api_key}
                )

        schema = vol.Schema(
            {
                vol.Required("scan_interval", default=current_interval): selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        mode=selector.NumberSelectorMode.BOX,
                        step=1,
                        unit_of_measurement="s",
                    )
                ),
                vol.Optional("api_key", default=current_key): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema, errors=errors)


class GatusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gatus."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Return the options flow handler."""
        return OptionsFlowHandler()

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
        """Handle re-authentication — show the reauth confirm form."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the reauth confirm step."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            api_key: str | None = user_input.get("api_key") or None

            try:
                await _validate_gatus_connection(
                    async_get_clientsession(self.hass),
                    entry.data["url"],
                    api_key,
                )
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                self.hass.config_entries.async_update_entry(
                    entry,
                    data={**entry.data, "api_key": api_key},
                )
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        schema = vol.Schema(
            {
                vol.Optional("api_key"): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle in-place URL and API key reconfiguration."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        current_url = entry.data.get("url", "")
        current_key = entry.data.get("api_key") or ""

        if user_input is not None:
            url: str = user_input["url"].rstrip("/")
            api_key: str | None = user_input.get("api_key") or None

            try:
                await _validate_gatus_connection(async_get_clientsession(self.hass), url, api_key)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(url.lower())
                self._abort_if_unique_id_configured(updates={"url": url})

                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={"url": url, "api_key": api_key},
                )

        schema = vol.Schema(
            {
                vol.Required("url", default=current_url): selector.TextSelector(),
                vol.Optional("api_key", default=current_key): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
                ),
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )
