"""Tests for snapshot-oriented models."""

from netmind.models import (
    AuditReport,
    DeviceSnapshot,
    Finding,
    FindingSeverity,
    Interface,
    Neighbor,
    Route,
)


def test_interface_defaults():
    iface = Interface(name="GigabitEthernet0/1")
    assert iface.name == "GigabitEthernet0/1"
    assert iface.ip_address == ""
    assert iface.crc_errors == 0


def test_route_fields():
    route = Route(code="O", prefix="10.10.10.0/24", next_hop="192.168.0.2")
    assert route.code == "O"
    assert route.prefix == "10.10.10.0/24"
    assert route.next_hop == "192.168.0.2"


def test_neighbor_fields():
    neighbor = Neighbor(device_id="DIST-1", local_interface="Gi0/1", remote_interface="Gi1/0/1")
    assert neighbor.device_id == "DIST-1"
    assert neighbor.local_interface == "Gi0/1"


def test_device_snapshot_holds_collections():
    snapshot = DeviceSnapshot(
        host="10.0.0.1",
        timestamp="2024-01-01T00:00:00+00:00",
        interfaces=[Interface(name="Gi0/1")],
        routes=[Route(code="C", prefix="10.0.0.0/24")],
        neighbors=[Neighbor(device_id="SW1")],
    )
    assert len(snapshot.interfaces) == 1
    assert len(snapshot.routes) == 1
    assert len(snapshot.neighbors) == 1


def test_audit_report_counts_with_finding_model():
    findings = [
        Finding(
            severity=FindingSeverity.CRITICAL,
            category="routing",
            title="Missing default route",
            detail="No default route",
            explanation="Traffic may fail",
            next_commands=["show ip route 0.0.0.0"],
        ),
        Finding(
            severity=FindingSeverity.WARNING,
            category="interface",
            title="Interface down",
            detail="Gi0/2 down",
            explanation="Unexpected link state",
            next_commands=["show interfaces Gi0/2"],
        ),
    ]
    report = AuditReport(host="10.0.0.1", timestamp="2024-01-01T00:00:00+00:00", findings=findings)
    assert report.critical_count == 1
    assert report.warning_count == 1
    assert report.info_count == 0
