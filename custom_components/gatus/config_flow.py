"""Config flow for the Gatus integration.

Phase 1 stub — config_flow.py must exist because manifest.json declares
config_flow: true. The flow is fully implemented in Phase 2.

Tests use MockConfigEntry which bypasses this flow entirely.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class GatusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gatus.

    Implemented in Phase 2. Raises NotImplementedError if called directly.
    """

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle the initial step — implemented in Phase 2."""
        raise NotImplementedError("Config flow async_step_user is implemented in Phase 2")

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        """Handle re-authentication — implemented in Phase 2.

        This stub prevents HA from raising UnknownStep when ConfigEntryAuthFailed
        triggers a reauth flow during tests (Pitfall 2 side-effect).
        """
        return self.async_abort(reason="reauth_not_implemented")
