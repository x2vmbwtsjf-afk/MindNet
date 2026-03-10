"""Tests for connector management commands and saved-connector resolution."""

from dataclasses import dataclass

from typer.testing import CliRunner

from netmind import cli
from netmind.security.config_store import ConnectorConfig
from netmind.security.credentials import ConnectorCredentials


runner = CliRunner()


@dataclass
class FakeStore:
    """In-memory credential store used for CLI tests."""

    metadata: dict[str, ConnectorConfig]
    secrets: dict[str, str]

    def save_connector_credentials(
        self,
        name: str,
        username: str,
        secret: str,
        host: str = "",
        platform: str = "",
        connector_type: str = "ssh",
    ) -> ConnectorConfig:
        config = ConnectorConfig(
            name=name,
            host=host,
            platform=platform,
            connector_type=connector_type,
            username=username,
        )
        self.metadata[name] = config
        self.secrets[name] = secret
        return config

    def list_connectors(self) -> list[ConnectorConfig]:
        return list(self.metadata.values())

    def load_connector_metadata(self, name: str) -> ConnectorConfig | None:
        return self.metadata.get(name)

    def load_connector_credentials(self, name: str) -> ConnectorCredentials | None:
        config = self.metadata.get(name)
        if config is None:
            return None
        return ConnectorCredentials(
            name=config.name,
            username=config.username,
            secret=self.secrets.get(name),
            host=config.host,
            platform=config.platform,
            connector_type=config.connector_type,
        )

    def delete_connector_credentials(self, name: str) -> None:
        self.metadata.pop(name, None)
        self.secrets.pop(name, None)


def test_connector_add_list_show_remove(monkeypatch):
    store = FakeStore(metadata={}, secrets={})
    monkeypatch.setattr(cli, "_get_credential_store", lambda: store)

    result = runner.invoke(
        cli.app,
        ["connector", "add"],
        input="\n".join([
            "lab-leaf",
            "ssh",
            "10.0.0.10",
            "cisco_ios",
            "admin",
            "super-secret",
            "super-secret",
        ]) + "\n",
    )
    assert result.exit_code == 0
    assert "Connector 'lab-leaf' saved" in result.stdout

    result = runner.invoke(cli.app, ["connector", "list"])
    assert result.exit_code == 0
    assert "lab-leaf" in result.stdout
    assert "super-secret" not in result.stdout

    result = runner.invoke(cli.app, ["connector", "show", "lab-leaf"])
    assert result.exit_code == 0
    assert "10.0.0.10" in result.stdout
    assert "admin" in result.stdout
    assert "super-secret" not in result.stdout

    result = runner.invoke(cli.app, ["connector", "remove", "lab-leaf"])
    assert result.exit_code == 0
    assert "Connector 'lab-leaf' removed" in result.stdout
    assert "lab-leaf" not in store.metadata


def test_connect_uses_saved_connector(monkeypatch):
    store = FakeStore(
        metadata={
            "lab-leaf": ConnectorConfig(
                name="lab-leaf",
                host="10.0.0.10",
                platform="cisco_ios",
                connector_type="ssh",
                username="admin",
            )
        },
        secrets={"lab-leaf": "super-secret"},
    )
    captured = {}

    def fake_test_connectivity(profile):
        captured["host"] = profile.host
        captured["username"] = profile.username
        captured["password"] = profile.password
        captured["connector_type"] = profile.connector_type
        return True, "ok"

    monkeypatch.setattr(cli, "_get_credential_store", lambda: store)
    monkeypatch.setattr(cli.ssh_client, "test_connectivity", fake_test_connectivity)

    result = runner.invoke(cli.app, ["connect", "lab-leaf"])
    assert result.exit_code == 0
    assert captured["host"] == "10.0.0.10"
    assert captured["username"] == "admin"
    assert captured["password"] == "super-secret"
    assert captured["connector_type"] == "ssh"


def test_connect_falls_back_to_direct_host(monkeypatch):
    store = FakeStore(metadata={}, secrets={})
    captured = {}

    def fake_test_connectivity(profile):
        captured["host"] = profile.host
        return True, "ok"

    monkeypatch.setattr(cli, "_get_credential_store", lambda: store)
    monkeypatch.setattr(cli.ssh_client, "test_connectivity", fake_test_connectivity)

    result = runner.invoke(
        cli.app,
        ["connect", "10.0.0.20", "--username", "admin", "--password", "pw"],
    )
    assert result.exit_code == 0
    assert captured["host"] == "10.0.0.20"
