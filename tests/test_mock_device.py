"""Tests for the MockDevice class."""

import pytest
from netmind.mock_device import MockDevice


class TestMockDevice:
    def setup_method(self):
        self.device = MockDevice("192.168.1.1")

    def test_known_command_returns_output(self):
        output = self.device.send_command("show version")
        assert "Cisco IOS Software" in output

    def test_case_insensitive_match(self):
        output = self.device.send_command("SHOW VERSION")
        assert "Cisco IOS Software" in output

    def test_unknown_command_returns_error(self):
        output = self.device.send_command("show something completely unknown xyz")
        assert "Invalid input" in output or "^" in output

    def test_disconnect_is_noop(self):
        # Should not raise
        self.device.disconnect()

    def test_all_audit_commands_have_mock_responses(self):
        from netmind.audit import AUDIT_COMMANDS
        for cmd in AUDIT_COMMANDS:
            output = self.device.send_command(cmd)
            assert output  # Non-empty response
            assert "[ERROR]" not in output
