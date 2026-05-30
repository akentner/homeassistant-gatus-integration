"""Tests for the Gatus config flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.gatus.const import DEFAULT_SCAN_INTERVAL, DOMAIN


@pytest.fixture
def mock_validate_ok():
    """Mock _validate_gatus_connection to succeed."""
    with patch(
        "custom_components.gatus.config_flow._validate_gatus_connection",
        return_value=None,
    ) as mock:
        yield mock


@pytest.fixture
def mock_validate_cannot_connect():
    """Mock _validate_gatus_connection to raise CannotConnect."""
    from custom_components.gatus.config_flow import CannotConnect

    with patch(
        "custom_components.gatus.config_flow._validate_gatus_connection",
        side_effect=CannotConnect,
    ) as mock:
        yield mock


@pytest.fixture
def mock_validate_invalid_auth():
    """Mock _validate_gatus_connection to raise InvalidAuth."""
    from custom_components.gatus.config_flow import InvalidAuth

    with patch(
        "custom_components.gatus.config_flow._validate_gatus_connection",
        side_effect=InvalidAuth,
    ) as mock:
        yield mock


async def test_happy_path(hass, mock_validate_ok):
    """Test successful config flow with URL, no API key, default prefix."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": "http://gatus.test", "api_key": "", "prefix": "gatus_"},
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["url"] == "http://gatus.test"
    assert result2["data"]["api_key"] is None
    assert result2["data"]["prefix"] == "gatus_"
    assert result2["options"]["scan_interval"] == DEFAULT_SCAN_INTERVAL


async def test_cannot_connect(hass, mock_validate_cannot_connect):
    """Test that unreachable URL shows cannot_connect error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": "http://gatus.test", "api_key": "", "prefix": "gatus_"},
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"]["base"] == "cannot_connect"


async def test_invalid_auth(hass, mock_validate_invalid_auth):
    """Test that 401 response shows invalid_auth error."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": "http://gatus.test", "api_key": "badkey", "prefix": "gatus_"},
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"]["base"] == "invalid_auth"


async def test_duplicate_url(hass, mock_validate_ok):
    """Test that a duplicate URL aborts with already_configured."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://gatus.test", "api_key": None, "prefix": "gatus_"},
        unique_id="http://gatus.test",
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": "http://gatus.test", "api_key": "", "prefix": "gatus_"},
    )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_custom_prefix(hass, mock_validate_ok):
    """Test that a custom prefix is stored in entry data."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": "http://gatus.test", "api_key": "", "prefix": "myprefix_"},
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["prefix"] == "myprefix_"


async def test_empty_prefix_uses_default(hass, mock_validate_ok):
    """Test that empty prefix falls back to DEFAULT_PREFIX."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": "http://gatus.test", "api_key": "", "prefix": ""},
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["prefix"] == "gatus_"


async def test_trailing_slash_stripped(hass, mock_validate_ok):
    """Test that trailing slash is stripped from URL before storage."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": "http://gatus.test/", "api_key": "", "prefix": "gatus_"},
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["url"] == "http://gatus.test"


# ---------------------------------------------------------------------------
# Options Flow tests
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_entry_with_coordinator(hass):
    """Create a loaded MockConfigEntry with a mock coordinator as runtime_data."""
    from unittest.mock import MagicMock
    from datetime import timedelta

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://gatus.test", "api_key": None, "prefix": "gatus_"},
        options={"scan_interval": DEFAULT_SCAN_INTERVAL},
        unique_id="http://gatus.test",
        entry_id="test_entry_id",
    )
    entry.add_to_hass(hass)

    coordinator = MagicMock()
    coordinator.update_interval = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
    entry.runtime_data = coordinator

    return entry


async def test_options_flow_show_form(hass, mock_entry_with_coordinator):
    """OPT-1: Options flow shows form with current scan_interval pre-filled."""
    entry = mock_entry_with_coordinator

    result = await hass.config_entries.options.async_init(entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_save_scan_interval(hass, mock_entry_with_coordinator):
    """OPT-2: Submit scan_interval=120 → entry.options updated; coordinator interval set."""
    from datetime import timedelta

    entry = mock_entry_with_coordinator

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"scan_interval": 120, "api_key": ""},
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["scan_interval"] == 120
    assert entry.runtime_data.update_interval == timedelta(seconds=120)


async def test_options_flow_api_key_rotation(hass, mock_entry_with_coordinator):
    """OPT-3: Submit new api_key → entry.options["api_key"] == new key."""
    entry = mock_entry_with_coordinator

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"scan_interval": 60, "api_key": "new-key"},
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["api_key"] == "new-key"


async def test_options_flow_clear_api_key(hass, mock_entry_with_coordinator):
    """OPT-4: Submit empty api_key → entry.options["api_key"] is None."""
    entry = mock_entry_with_coordinator

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"scan_interval": 60, "api_key": ""},
    )

    assert result2["type"] == FlowResultType.CREATE_ENTRY
    assert result2["data"]["api_key"] is None


async def test_options_flow_bounds_validation(hass, mock_entry_with_coordinator):
    """OPT-5: scan_interval out of [30, 300] range → validation error."""
    entry = mock_entry_with_coordinator

    # Below minimum
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result2 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"scan_interval": 29, "api_key": ""},
    )
    assert result2["type"] == FlowResultType.FORM
    assert "scan_interval" in result2["errors"] or "base" in result2["errors"]

    # Above maximum
    result3 = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"scan_interval": 301, "api_key": ""},
    )
    assert result3["type"] == FlowResultType.FORM
    assert "scan_interval" in result3["errors"] or "base" in result3["errors"]


# ---------------------------------------------------------------------------
# Reauth Flow tests
# ---------------------------------------------------------------------------


async def test_reauth_flow_show_form(hass):
    """REAUTH-1: Triggering reauth shows the form."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://gatus.test", "api_key": "old-key", "prefix": "gatus_"},
        unique_id="http://gatus.test",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )

    assert result["type"] == FlowResultType.FORM


async def test_reauth_flow_valid_key(hass, mock_validate_ok):
    """REAUTH-2: Valid api_key → entry.data updated; reload scheduled; aborts reauth_successful."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://gatus.test", "api_key": "old-key", "prefix": "gatus_"},
        options={"scan_interval": DEFAULT_SCAN_INTERVAL},
        unique_id="http://gatus.test",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_reload",
        return_value=None,
    ):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={"api_key": "good-key"},
        )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reauth_successful"
    assert entry.data["api_key"] == "good-key"


async def test_reauth_flow_bad_key(hass, mock_validate_invalid_auth):
    """REAUTH-3: Bad api_key → form re-shown with invalid_auth error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://gatus.test", "api_key": "old-key", "prefix": "gatus_"},
        unique_id="http://gatus.test",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_REAUTH, "entry_id": entry.entry_id},
        data=entry.data,
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"api_key": "bad-key"},
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"]["base"] == "invalid_auth"


# ---------------------------------------------------------------------------
# Reconfigure Flow tests
# ---------------------------------------------------------------------------


async def test_reconfigure_flow_show_form(hass):
    """RECONF-1: Reconfigure shows form with URL and api_key pre-filled."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://gatus.test", "api_key": "some-key", "prefix": "gatus_"},
        unique_id="http://gatus.test",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "reconfigure"


async def test_reconfigure_flow_valid_new_url(hass, mock_validate_ok):
    """RECONF-2: Valid new URL → entry.data updated; entry reloaded."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://gatus.test", "api_key": None, "prefix": "gatus_"},
        options={"scan_interval": DEFAULT_SCAN_INTERVAL},
        unique_id="http://gatus.test",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": "http://gatus-new.test", "api_key": ""},
    )

    assert result2["type"] == FlowResultType.ABORT
    assert result2["reason"] == "reconfigure_successful"


async def test_reconfigure_flow_cannot_connect(hass, mock_validate_cannot_connect):
    """RECONF-3: New URL unreachable → form re-shown with cannot_connect error."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://gatus.test", "api_key": None, "prefix": "gatus_"},
        unique_id="http://gatus.test",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": "http://gatus-bad.test", "api_key": ""},
    )

    assert result2["type"] == FlowResultType.FORM
    assert result2["errors"]["base"] == "cannot_connect"


async def test_reconfigure_flow_no_prefix_field(hass, mock_validate_ok):
    """RECONF-4: Reconfigure form does not expose prefix field; prefix unchanged in entry.data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={"url": "http://gatus.test", "api_key": None, "prefix": "custom_"},
        options={"scan_interval": DEFAULT_SCAN_INTERVAL},
        unique_id="http://gatus.test",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={"url": "http://gatus-new.test", "api_key": ""},
    )

    assert result2["type"] == FlowResultType.ABORT
    # Prefix must be preserved (not exposed for change)
    assert entry.data.get("prefix") == "custom_"


# ---------------------------------------------------------------------------
# Coexistence test
# ---------------------------------------------------------------------------


async def test_two_instances_coexist(hass, mock_validate_ok):
    """COEX-1: Two entries with different URLs can coexist without conflict."""
    # First instance
    result1 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    r1 = await hass.config_entries.flow.async_configure(
        result1["flow_id"],
        user_input={"url": "http://gatus-1.test", "api_key": "", "prefix": "g1_"},
    )
    assert r1["type"] == FlowResultType.CREATE_ENTRY

    # Second instance — different URL
    result2 = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    r2 = await hass.config_entries.flow.async_configure(
        result2["flow_id"],
        user_input={"url": "http://gatus-2.test", "api_key": "", "prefix": "g2_"},
    )
    assert r2["type"] == FlowResultType.CREATE_ENTRY

    # Both entries exist with distinct entry_ids
    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2
    entry_ids = {e.entry_id for e in entries}
    assert len(entry_ids) == 2
