"""Tests for connector resolution and SSH connector behavior."""

from netmind.connectors.api import APIConnector
from netmind.connectors.manager import get_connector
from netmind.connectors.ssh import SSHConnector
from netmind.models import DeviceProfile


def test_manager_resolves_ssh_connector():
    profile = DeviceProfile(host="10.0.0.1", username="user", password="pass")
    connector = get_connector(profile)
    assert isinstance(connector, SSHConnector)


def test_manager_resolves_api_connector():
    profile = DeviceProfile(host="controller", username="user", password="pass", connector_type="api")
    connector = get_connector(profile)
    assert isinstance(connector, APIConnector)


def test_ssh_connector_runs_in_mock_mode(monkeypatch):
    monkeypatch.setenv("NETMIND_MOCK", "true")
    profile = DeviceProfile(host="10.0.0.1", username="user", password="pass")
    connector = SSHConnector(profile)
    output = connector.run_command("show version")
    assert "Cisco IOS Software" in output
    connector.close()


def test_ssh_connector_reports_mock_connectivity(monkeypatch):
    monkeypatch.setenv("NETMIND_MOCK", "true")
    profile = DeviceProfile(host="10.0.0.1", username="user", password="pass")
    connector = SSHConnector(profile)
    success, message = connector.test_connectivity()
    assert success is True
    assert "[MOCK]" in message
