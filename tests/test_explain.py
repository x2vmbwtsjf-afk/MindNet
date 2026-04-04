"""
Unit tests for the NetMind explain / analysis engine.

These tests do not require SSH access — they work entirely on static
mock output strings from the mock_device module.
"""

import pytest
from netmind.explain import (
    analyze_report,
    analyze_offline_output,
    build_snapshot,
    detect_command_type,
    findings_from_snapshot,
    explain_command_output,
    _parse_ip_interface_brief,
    _parse_route_table,
    _parse_cdp_neighbors,
    _parse_interfaces_detail,
)
from netmind.models import AuditReport, FindingSeverity, Interface, Neighbor, Route
from netmind.mock_device import MOCK_RESPONSES


# ---------------------------------------------------------------------------
# Parser tests
# ---------------------------------------------------------------------------

class TestParseIpInterfaceBrief:
    def test_parses_correct_count(self):
        ifaces = _parse_ip_interface_brief(MOCK_RESPONSES["show ip interface brief"])
        assert len(ifaces) == 6  # Gi0/0, Gi0/1, Gi0/2, Gi0/3, Lo0, Tu0
        assert all(isinstance(iface, Interface) for iface in ifaces)

    def test_identifies_down_interface(self):
        ifaces = _parse_ip_interface_brief(MOCK_RESPONSES["show ip interface brief"])
        down = [i for i in ifaces if "down" in i.status.lower() and "admin" not in i.status.lower()]
        assert any(i.name == "GigabitEthernet0/3" for i in down)

    def test_identifies_admin_down(self):
        ifaces = _parse_ip_interface_brief(MOCK_RESPONSES["show ip interface brief"])
        admin_down = [i for i in ifaces if "administratively down" in i.status.lower()]
        assert any(i.name == "GigabitEthernet0/2" for i in admin_down)


class TestParseRouteTable:
    def test_detects_default_route(self):
        routes = _parse_route_table(MOCK_RESPONSES["show ip route"])
        assert all(isinstance(route, Route) for route in routes)
        assert any(route.prefix == "0.0.0.0/0" for route in routes)

    def test_counts_connected_routes(self):
        routes = _parse_route_table(MOCK_RESPONSES["show ip route"])
        connected = [route for route in routes if route.code == "C"]
        assert len(connected) >= 2

    def test_no_default_route(self):
        empty_table = "Codes: C - connected\n\n10.0.0.0/8 is directly connected, Gi0/0"
        routes = _parse_route_table(empty_table)
        assert all(route.prefix != "0.0.0.0/0" for route in routes)


class TestParseCdpNeighbors:
    def test_finds_one_neighbor(self):
        neighbors = _parse_cdp_neighbors(MOCK_RESPONSES["show cdp neighbors"])
        assert all(isinstance(neighbor, Neighbor) for neighbor in neighbors)
        assert any(neighbor.device_id == "SW-CORE-01" for neighbor in neighbors)
        assert any(neighbor.platform == "WS-C3750" for neighbor in neighbors)

    def test_no_neighbors(self):
        no_neighbor_output = (
            "Capability Codes: R - Router\n\n"
            "Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID\n"
            "Total cdp entries displayed : 0"
        )
        neighbors = _parse_cdp_neighbors(no_neighbor_output)
        assert neighbors == []


class TestParseInterfaceDetail:
    def test_parses_error_counters(self):
        ifaces = _parse_interfaces_detail(MOCK_RESPONSES["show interfaces"])
        gi3 = next((i for i in ifaces if "GigabitEthernet0/3" in i.name), None)
        assert gi3 is not None
        assert gi3.crc_errors == 32
        assert gi3.input_errors == 147


# ---------------------------------------------------------------------------
# Analyzer / finding tests
# ---------------------------------------------------------------------------

class TestAnalyzeReport:
    def _make_mock_report(self) -> AuditReport:
        return AuditReport(
            host="10.0.0.1",
            timestamp="2024-01-01T00:00:00+00:00",
            raw_outputs={cmd: MOCK_RESPONSES[cmd] for cmd in MOCK_RESPONSES if not cmd.startswith("show interfaces gi")},
        )

    def test_report_has_findings(self):
        report = analyze_report(self._make_mock_report())
        assert len(report.findings) > 0
        assert report.snapshot is not None

    def test_finds_interface_down(self):
        report = analyze_report(self._make_mock_report())
        titles = [f.title for f in report.findings]
        assert any("GigabitEthernet0/3" in t for t in titles)

    def test_finds_admin_down_as_info(self):
        report = analyze_report(self._make_mock_report())
        info_findings = [f for f in report.findings if f.severity == FindingSeverity.INFO]
        assert any("admin" in f.title.lower() or "GigabitEthernet0/2" in f.title for f in info_findings)

    def test_critical_findings_sorted_first(self):
        report = analyze_report(self._make_mock_report())
        if len(report.findings) > 1:
            severities = [f.severity for f in report.findings]
            # Verify no WARNING before CRITICAL
            seen_non_critical = False
            for s in severities:
                if s != FindingSeverity.CRITICAL:
                    seen_non_critical = True
                if s == FindingSeverity.CRITICAL and seen_non_critical:
                    pytest.fail("CRITICAL finding appears after non-CRITICAL finding")

    def test_each_finding_has_next_commands(self):
        report = analyze_report(self._make_mock_report())
        for finding in report.findings:
            assert len(finding.next_commands) >= 1, f"Finding '{finding.title}' has no next_commands"

    def test_default_route_present(self):
        report = analyze_report(self._make_mock_report())
        routing_critical = [
            f for f in report.findings
            if f.category == "routing" and f.severity == FindingSeverity.CRITICAL
        ]
        # Mock data has a default route, so no critical routing finding expected
        assert len(routing_critical) == 0


class TestExplainCommandOutput:
    def test_show_version_explanation(self):
        result = explain_command_output("show version", MOCK_RESPONSES["show version"])
        assert "summary" in result
        assert len(result["next_commands"]) > 0

    def test_show_ip_interface_brief_counts(self):
        result = explain_command_output(
            "show ip interface brief", MOCK_RESPONSES["show ip interface brief"]
        )
        assert "summary" in result
        # Should mention the down interface
        assert "GigabitEthernet0/3" in result["summary"]

    def test_show_ip_route_default_present(self):
        result = explain_command_output("show ip route", MOCK_RESPONSES["show ip route"])
        assert "default route is present" in result["summary"].lower()

    def test_unknown_command_fallback(self):
        result = explain_command_output("show something obscure", "some output\nmore output")
        assert "summary" in result
        assert len(result["next_commands"]) > 0


class TestOfflineAnalysis:
    def test_detects_ip_interface_brief_type(self):
        detected = detect_command_type(MOCK_RESPONSES["show ip interface brief"])
        assert detected == "ip-int-brief"

    def test_detects_interfaces_status_type(self):
        output = (
            "Port      Name               Status       Vlan       Duplex  Speed Type\n"
            "Gi1/0/3                      err-disabled 20         a-full  a-1000 10/100/1000BaseTX\n"
        )
        detected = detect_command_type(output)
        assert detected == "interfaces-status"

    def test_analyzes_interfaces_status_offline(self):
        output = (
            "Port      Name               Status       Vlan       Duplex  Speed Type\n"
            "Gi1/0/3                      err-disabled 20         a-full  a-1000 10/100/1000BaseTX\n"
        )
        command, snapshot, findings, explanation = analyze_offline_output(output)
        assert command == "show interfaces status"
        assert len(snapshot.interfaces) == 1
        assert any("err-disabled" in finding.title.lower() for finding in findings)
        assert "summary" in explanation


class TestSnapshotPipeline:
    def test_build_snapshot_contains_models(self):
        raw_outputs = {
            cmd: MOCK_RESPONSES[cmd]
            for cmd in MOCK_RESPONSES
            if not cmd.startswith("show interfaces gi")
        }
        snapshot = build_snapshot("10.0.0.1", "2024-01-01T00:00:00+00:00", raw_outputs)
        assert snapshot.host == "10.0.0.1"
        assert len(snapshot.interfaces) > 0
        assert len(snapshot.routes) > 0
        assert len(snapshot.neighbors) > 0

    def test_findings_from_snapshot_returns_findings(self):
        raw_outputs = {
            cmd: MOCK_RESPONSES[cmd]
            for cmd in MOCK_RESPONSES
            if not cmd.startswith("show interfaces gi")
        }
        snapshot = build_snapshot("10.0.0.1", "2024-01-01T00:00:00+00:00", raw_outputs)
        findings = findings_from_snapshot(snapshot)
        assert len(findings) > 0
