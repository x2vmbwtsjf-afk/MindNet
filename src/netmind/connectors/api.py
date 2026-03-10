"""Placeholder API connector for future non-SSH transports."""

from __future__ import annotations

from .base import BaseConnector


class APIConnector(BaseConnector):
    """Stub connector reserved for future API-based integrations."""

    def connect(self) -> None:
        raise NotImplementedError("API connector is not implemented yet.")

    def run_command(self, command: str) -> str:
        raise NotImplementedError("API connector is not implemented yet.")

    def close(self) -> None:
        return None
