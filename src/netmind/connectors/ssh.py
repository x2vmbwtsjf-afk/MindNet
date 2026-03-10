"""SSH connector implementation backed by Netmiko or mock mode."""

from __future__ import annotations

import os
import time
from typing import Any

from ..mock_device import MockDevice
from ..models import DeviceProfile
from .base import BaseConnector


def _is_mock_mode() -> bool:
    """Return True when mock mode is enabled for local development."""
    return os.environ.get("NETMIND_MOCK", "").strip().lower() in {"1", "true", "yes", "on"}


class SSHConnector(BaseConnector):
    """SSH connector using Netmiko for live sessions and MockDevice for offline runs."""

    def __init__(self, profile: DeviceProfile) -> None:
        super().__init__(profile)
        self._connection: Any | None = None

    def connect(self) -> None:
        """Open an SSH session if one is not already active."""
        if self._connection is not None:
            return

        if _is_mock_mode():
            self._connection = MockDevice(self.profile.host)
            return

        try:
            from netmiko import ConnectHandler
        except ImportError as exc:
            raise RuntimeError(
                "Netmiko is not installed. Run: pip install netmiko\n"
                "Or set NETMIND_MOCK=true to use the built-in mock device."
            ) from exc

        conn_params = {
            "device_type": self.profile.device_type,
            "host": self.profile.host,
            "username": self.profile.username,
            "password": self.profile.password,
            "port": self.profile.port,
            "timeout": self.profile.timeout,
            "secret": self.profile.secret,
        }

        self._connection = ConnectHandler(**conn_params)
        if self.profile.secret:
            self._connection.enable()

    def run_command(self, command: str) -> str:
        """Execute a command over the active SSH session."""
        self.connect()
        return self._connection.send_command(command)

    def close(self) -> None:
        """Disconnect the active SSH session if present."""
        if self._connection is None:
            return
        self._connection.disconnect()
        self._connection = None

    def test_connectivity(self) -> tuple[bool, str]:
        """Test SSH connectivity with transport-specific messaging."""
        if _is_mock_mode():
            return True, f"[MOCK] SSH connection to {self.profile.host}:{self.profile.port} successful."

        start = time.monotonic()
        try:
            self.connect()
            elapsed = time.monotonic() - start
            return True, (
                f"SSH connection to {self.profile.host}:{self.profile.port} successful "
                f"({elapsed:.2f}s)."
            )
        except Exception as exc:
            return False, f"Connection failed: {exc}"
        finally:
            self.close()
