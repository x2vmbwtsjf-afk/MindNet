"""Tests for MindNet shell UX and prompt behavior."""

from contextlib import redirect_stdout
from io import StringIO

from netmind.shell import BANNER, NetMindShell


def test_banner_uses_mindnet_branding():
    assert "MindNet" in BANNER
    assert "AI Infrastructure Brain" in BANNER
    assert "Quick start" in BANNER
    assert "Cisco-like" not in BANNER


def test_default_prompt_is_mindnet():
    shell = NetMindShell()
    assert shell.prompt == "mindnet> "


def test_connect_sets_context_prompt_for_hostname():
    shell = NetMindShell()
    buffer = StringIO()
    with redirect_stdout(buffer):
        shell._execute("connect leaf3", {})
    assert shell.prompt == "mindnet:leaf3> "
    assert "MindNet session ready" in buffer.getvalue()


def test_connect_sets_fallback_prompt_for_ip():
    shell = NetMindShell()
    buffer = StringIO()
    with redirect_stdout(buffer):
        shell._execute("connect 10.0.0.1", {})
    assert shell.prompt == "mindnet:connected> "
    assert "Status: connected" in buffer.getvalue()


def test_help_output_uses_modern_sections():
    shell = NetMindShell()
    buffer = StringIO()
    with redirect_stdout(buffer):
        shell.do_help("")
    output = buffer.getvalue()
    assert "Session Workflow" in output
    assert "Context and Analysis" in output
    assert "Simulation" in output
    assert "Utilities" in output
    assert "Cisco-like" not in output


def test_show_status_is_available_in_shell():
    shell = NetMindShell()
    buffer = StringIO()
    with redirect_stdout(buffer):
        shell._execute("show status", {})
    output = buffer.getvalue()
    assert "Infrastructure Status" in output
    assert "Health score" in output
    assert "Priority actions" in output
