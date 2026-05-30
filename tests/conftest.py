"""Pytest configuration and shared fixtures for Gatus integration tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure custom_components is importable from the project root
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def enable_custom_integrations(hass):  # type: ignore[no-untyped-def]
    """Enable loading of custom integrations in the test Home Assistant instance."""
    hass.data.pop("custom_components", None)
    return hass
