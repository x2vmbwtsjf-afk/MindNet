"""CLI product-level tests for entrypoints and offline analysis commands."""

from pathlib import Path

from typer.testing import CliRunner

from netmind.cli import app


runner = CliRunner()


def test_no_args_prints_product_overview():
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "MindNet" in result.stdout
    assert "local-first infrastructure intelligence console" in result.stdout
    assert "Quick start" in result.stdout


def test_help_uses_mindnet_branding():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "MindNet" in result.stdout
    assert "AI Infrastructure Brain" in result.stdout


def test_version_command_prints_product_name():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "MindNet" in result.stdout
    assert "AI Infrastructure Brain" in result.stdout


def test_status_command_renders_dashboard_in_mock_mode(monkeypatch):
    monkeypatch.setenv("NETMIND_MOCK", "true")
    result = runner.invoke(app, ["status", "10.0.0.1"])
    assert result.exit_code == 0
    assert "Infrastructure Status" in result.stdout
    assert "Health score" in result.stdout
    assert "Snapshot age" in result.stdout
    assert "Topology Context" in result.stdout
    assert "Platforms/modul" in result.stdout
    assert "Findings Breakdown" in result.stdout
    assert "Interface Spotlight" in result.stdout
    assert "Top Findings" in result.stdout
    assert "Recommended Actions" in result.stdout
    assert "Summary" in result.stdout
    assert "Interfaces" in result.stdout
    assert "Routing" in result.stdout
    assert "10.0.0.1" in result.stdout


def test_analyze_file_with_auto_detect(tmp_path: Path):
    sample = tmp_path / "interfaces-status.txt"
    sample.write_text(
        "Port      Name               Status       Vlan       Duplex  Speed Type\n"
        "Gi1/0/3                      err-disabled 20         a-full  a-1000 10/100/1000BaseTX\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["analyze-file", str(sample)])
    assert result.exit_code == 0
    assert "show interfaces status" in result.stdout
    assert "err-disabled" in result.stdout.lower()


def test_explain_output_from_stdin():
    output = (
        "Codes: C - connected, S - static, O - OSPF\n\n"
        "Gateway of last resort is 10.10.10.254 to network 0.0.0.0\n\n"
        "S*    0.0.0.0/0 [1/0] via 10.10.10.254\n"
        "C     10.10.10.0/24 is directly connected, GigabitEthernet1/0/1\n"
    )
    result = runner.invoke(app, ["explain-output"], input=output)
    assert result.exit_code == 0
    assert "show ip route" in result.stdout
    assert "default route is present" in result.stdout.lower()
