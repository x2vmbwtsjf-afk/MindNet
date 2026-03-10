"""Credential storage service backed by OS keyring."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .config_store import ConnectorConfig, ConnectorConfigStore

KEYRING_SERVICE_NAME = "MindNet"


class KeyringBackend(Protocol):
    """Protocol for keyring-compatible secret backends."""

    def set_password(self, service_name: str, username: str, password: str) -> None:
        """Store a secret in the keyring."""

    def get_password(self, service_name: str, username: str) -> str | None:
        """Retrieve a secret from the keyring."""

    def delete_password(self, service_name: str, username: str) -> None:
        """Delete a secret from the keyring."""


@dataclass
class ConnectorCredentials:
    """Resolved connector credentials assembled from config metadata and keyring."""

    name: str
    username: str
    secret: str | None
    host: str = ""
    platform: str = ""
    connector_type: str = "ssh"


class SystemKeyringBackend:
    """Adapter around the `keyring` package for production use."""

    def __init__(self) -> None:
        try:
            import keyring
        except ImportError as exc:
            raise RuntimeError(
                "keyring is not installed. Run: pip install keyring"
            ) from exc
        self._keyring = keyring

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self._keyring.set_password(service_name, username, password)

    def get_password(self, service_name: str, username: str) -> str | None:
        return self._keyring.get_password(service_name, username)

    def delete_password(self, service_name: str, username: str) -> None:
        self._keyring.delete_password(service_name, username)


class CredentialStore:
    """Service that stores connector metadata locally and secrets in keyring."""

    def __init__(
        self,
        config_store: ConnectorConfigStore | None = None,
        keyring_backend: KeyringBackend | None = None,
        service_name: str = KEYRING_SERVICE_NAME,
    ) -> None:
        self._config_store = config_store or ConnectorConfigStore()
        self._keyring = keyring_backend or SystemKeyringBackend()
        self._service_name = service_name

    def save_connector_credentials(
        self,
        name: str,
        username: str,
        secret: str,
        host: str = "",
        platform: str = "",
        connector_type: str = "ssh",
    ) -> ConnectorConfig:
        """Save connector metadata locally and the secret in the OS keyring."""
        config = ConnectorConfig(
            name=name,
            host=host,
            platform=platform,
            connector_type=connector_type,
            username=username,
        )
        self._config_store.save(config)
        self._keyring.set_password(self._service_name, name, secret)
        return config

    def list_connectors(self) -> list[ConnectorConfig]:
        """List all stored connector metadata records."""
        return list(self._config_store.load_all().values())

    def load_connector_metadata(self, name: str) -> ConnectorConfig | None:
        """Load connector metadata without resolving secrets."""
        return self._config_store.load(name)

    def load_connector_credentials(self, name: str) -> ConnectorCredentials | None:
        """Load connector metadata from config and secret from keyring."""
        config = self._config_store.load(name)
        if config is None:
            return None

        secret = self._keyring.get_password(self._service_name, name)
        return ConnectorCredentials(
            name=config.name,
            username=config.username,
            secret=secret,
            host=config.host,
            platform=config.platform,
            connector_type=config.connector_type,
        )

    def delete_connector_credentials(self, name: str) -> None:
        """Delete connector metadata and its keyring secret."""
        self._config_store.delete(name)
        try:
            self._keyring.delete_password(self._service_name, name)
        except Exception:
            # Missing keyring entries should not break local cleanup flows.
            return
