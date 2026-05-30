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
