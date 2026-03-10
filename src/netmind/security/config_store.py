"""Local config storage for non-sensitive connector metadata."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ConnectorConfig:
    """Non-sensitive connector metadata stored in a local config file."""

    name: str
    host: str
    platform: str
    connector_type: str
    username: str = ""


class ConnectorConfigStore:
    """JSON-backed local store for connector metadata."""

    def __init__(self, path: str | Path | None = None) -> None:
        self._path = Path(path).expanduser().resolve() if path else self._default_path()

    @property
    def path(self) -> Path:
        """Return the resolved config file path."""
        return self._path

    def load_all(self) -> dict[str, ConnectorConfig]:
        """Load all stored connector metadata records."""
        payload = self._read_payload()
        return {
            name: ConnectorConfig(**record)
            for name, record in payload.items()
        }

    def load(self, name: str) -> ConnectorConfig | None:
        """Load one connector metadata record by name."""
        return self.load_all().get(name)

    def save(self, config: ConnectorConfig) -> ConnectorConfig:
        """Persist one connector metadata record."""
        payload = self._read_payload()
        payload[config.name] = asdict(config)
        self._write_payload(payload)
        return config

    def delete(self, name: str) -> None:
        """Delete one connector metadata record if present."""
        payload = self._read_payload()
        if name in payload:
            del payload[name]
            self._write_payload(payload)

    def _read_payload(self) -> dict[str, dict]:
        if not self._path.exists():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _write_payload(self, payload: dict[str, dict]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def _default_path(self) -> Path:
        env_path = os.environ.get("NETMIND_CONNECTOR_CONFIG")
        if env_path:
            return Path(env_path).expanduser().resolve()
        config_dir = _default_config_dir()
        return config_dir / "connectors.json"


def _default_config_dir() -> Path:
    """Return the OS-appropriate config directory for MindNet metadata."""
    home = Path.home()

    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "MindNet"

    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        base_dir = Path(appdata) if appdata else home / "AppData" / "Roaming"
        return base_dir / "MindNet"

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    base_dir = Path(xdg_config_home) if xdg_config_home else home / ".config"
    return base_dir / "mindnet"
