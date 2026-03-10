"""Tests for secure connector metadata and credential storage services."""

from pathlib import Path

from netmind.security.config_store import ConnectorConfig, ConnectorConfigStore
from netmind.security.credentials import CredentialStore


class FakeKeyringBackend:
    """In-memory keyring backend for deterministic tests."""

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], str] = {}

    def set_password(self, service_name: str, username: str, password: str) -> None:
        self._store[(service_name, username)] = password

    def get_password(self, service_name: str, username: str) -> str | None:
        return self._store.get((service_name, username))

    def delete_password(self, service_name: str, username: str) -> None:
        if (service_name, username) not in self._store:
            raise KeyError(username)
        del self._store[(service_name, username)]


def test_config_store_saves_only_metadata(tmp_path: Path):
    store = ConnectorConfigStore(tmp_path / "connectors.json")
    config = ConnectorConfig(
        name="lab-leaf",
        host="10.0.0.10",
        platform="cisco_ios",
        connector_type="ssh",
        username="admin",
    )
    store.save(config)

    payload = store.path.read_text(encoding="utf-8")
    assert "admin" in payload
    assert "10.0.0.10" in payload
    assert "password" not in payload
    assert "token" not in payload


def test_credential_store_round_trip(tmp_path: Path):
    config_store = ConnectorConfigStore(tmp_path / "connectors.json")
    keyring_backend = FakeKeyringBackend()
    store = CredentialStore(config_store=config_store, keyring_backend=keyring_backend)

    store.save_connector_credentials(
        name="lab-leaf",
        username="admin",
        secret="super-secret-password",
        host="10.0.0.10",
        platform="cisco_ios",
        connector_type="ssh",
    )

    loaded = store.load_connector_credentials("lab-leaf")
    assert loaded is not None
    assert loaded.username == "admin"
    assert loaded.secret == "super-secret-password"
    assert loaded.host == "10.0.0.10"

    payload = config_store.path.read_text(encoding="utf-8")
    assert "super-secret-password" not in payload


def test_delete_connector_credentials_removes_config_and_secret(tmp_path: Path):
    config_store = ConnectorConfigStore(tmp_path / "connectors.json")
    keyring_backend = FakeKeyringBackend()
    store = CredentialStore(config_store=config_store, keyring_backend=keyring_backend)

    store.save_connector_credentials(
        name="lab-api",
        username="svc-user",
        secret="api-token",
        host="controller.local",
        platform="controller",
        connector_type="api",
    )
    store.delete_connector_credentials("lab-api")

    assert store.load_connector_credentials("lab-api") is None
