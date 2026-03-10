"""Base connector abstraction for device access backends."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import DeviceProfile


class BaseConnector(ABC):
    """Abstract connector interface for transport-specific implementations."""

    def __init__(self, profile: DeviceProfile) -> None:
        self.profile = profile

    @abstractmethod
    def connect(self) -> None:
        """Establish the underlying transport session."""

    @abstractmethod
    def run_command(self, command: str) -> str:
        """Execute a command and return raw output."""

    @abstractmethod
    def close(self) -> None:
        """Close the underlying transport session."""

    def test_connectivity(self) -> tuple[bool, str]:
        """Attempt to connect and close, returning a success flag and message."""
        try:
            self.connect()
            return True, f"Connection to {self.profile.host}:{self.profile.port} successful."
        except Exception as exc:
            return False, f"Connection failed: {exc}"
        finally:
            self.close()

    def __enter__(self) -> "BaseConnector":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, exc_tb) -> None:
        self.close()
