"""Connector resolution and factory helpers."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from ..models import DeviceProfile
from .api import APIConnector
from .base import BaseConnector
from .ssh import SSHConnector


def get_connector(profile: DeviceProfile) -> BaseConnector:
    """Return the appropriate connector implementation for a device profile."""
    connector_type = profile.connector_type.strip().lower()
    if connector_type == "ssh":
        return SSHConnector(profile)
    if connector_type == "api":
        return APIConnector(profile)
    raise ValueError(f"Unsupported connector type: {profile.connector_type}")


@contextmanager
def open_connector(profile: DeviceProfile) -> Generator[BaseConnector]:
    """Open the resolved connector as a managed context."""
    connector = get_connector(profile)
    try:
        connector.connect()
        yield connector
    finally:
        connector.close()
