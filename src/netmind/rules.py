"""Deterministic rule engine for DeviceSnapshot analysis."""

from __future__ import annotations

from typing import Callable

from .models import DeviceSnapshot, Finding, FindingSeverity, Interface, Neighbor, Route

Rule = Callable[[DeviceSnapshot], list[Finding]]


def _route_stats(routes: list[Route]) -> tuple[bool, dict[str, int]]:
    """Return route health stats from normalized route entries."""
    has_default = any(route.prefix == "0.0.0.0/0" for route in routes)
    protocol_counts: dict[str, int] = {}
    for route in routes:
        protocol_counts[route.code] = protocol_counts.get(route.code, 0) + 1
    return has_default, protocol_counts


def check_interfaces_down(snapshot: DeviceSnapshot) -> list[Finding]:
    """Flag interfaces that are down but not administratively down."""
    findings: list[Finding] = []
    for iface in snapshot.interfaces:
        if not iface.protocol:
            continue
        status = iface.status.lower()
        protocol = iface.protocol.lower()
        if "down" in status and "admin" not in status and "admin" not in protocol:
            findings.append(
                Finding(
                    severity=FindingSeverity.WARNING,
                    category="interface",
                    title=f"{iface.name} is down",
                    detail=(
                        f"Interface {iface.name} has status='{iface.status}' "
                        f"and protocol='{iface.protocol}'. It is not administratively shut down, "
                        "which means the link is unexpectedly inactive."
                    ),
                    explanation=(
                        f"{iface.name} is expected to be up but is currently down. "
                        "This could indicate a physical cable issue, a problem with the connected device, "
                        "a duplex/speed mismatch, or a recent failure event. "
                        "If this interface is not in use, consider shutting it down intentionally."
                    ),
                    next_commands=[
                        f"show interfaces {iface.name}",
                        f"show log | include {iface.name}",
                        f"show interfaces {iface.name} counters errors",
                    ],
                )
            )
    return findings


def check_admin_down(snapshot: DeviceSnapshot) -> list[Finding]:
    """Report administratively down interfaces as informational findings."""
    findings: list[Finding] = []
    for iface in snapshot.interfaces:
        if "administratively down" in iface.status.lower():
            findings.append(
                Finding(
                    severity=FindingSeverity.INFO,
                    category="interface",
                    title=f"{iface.name} is administratively shut down",
                    detail=f"Interface {iface.name} has been manually shut down (status='{iface.status}').",
                    explanation=(
                        f"{iface.name} was intentionally disabled with a 'shutdown' command. "
                        "This is normal for unused ports. Verify this is intentional and document it "
                        "if it is a permanent change."
                    ),
                    next_commands=[
                        f"show interfaces {iface.name}",
                        f"show run interface {iface.name}",
                    ],
                )
            )
    return findings


def check_err_disabled(snapshot: DeviceSnapshot) -> list[Finding]:
    """Flag err-disabled ports from switchport or detail states."""
    findings: list[Finding] = []
    for iface in snapshot.interfaces:
        switchport_state = iface.switchport_status.lower()
        detail_state = iface.status.lower()
        if "err" in switchport_state or "err-disabled" in detail_state:
            findings.append(
                Finding(
                    severity=FindingSeverity.CRITICAL,
                    category="interface",
                    title=f"Port {iface.name} is err-disabled",
                    detail=(
                        f"Port {iface.name} appears in err-disabled state "
                        f"(switchport='{iface.switchport_status}', detail='{iface.status}')."
                    ),
                    explanation=(
                        f"{iface.name} has been automatically shut down by a protection feature. "
                        "The port will not recover on its own until the root cause is fixed and the "
                        "interface is re-enabled."
                    ),
                    next_commands=[
                        f"show interfaces {iface.name}",
                        f"show port-security interface {iface.name}",
                        f"show log | include {iface.name}",
                        "show errdisable recovery",
                    ],
                )
            )
    return findings


def check_interface_errors(snapshot: DeviceSnapshot) -> list[Finding]:
    """Flag interfaces with CRC/input error counters."""
    findings: list[Finding] = []
    for iface in snapshot.interfaces:
        if iface.crc_errors > 0 or iface.input_errors > 100:
            severity = FindingSeverity.CRITICAL if iface.crc_errors > 10 else FindingSeverity.WARNING
            findings.append(
                Finding(
                    severity=severity,
                    category="interface-errors",
                    title=(
                        f"{iface.name} has interface errors "
                        f"(CRC: {iface.crc_errors}, Input: {iface.input_errors})"
                    ),
                    detail=(
                        f"Interface {iface.name}: CRC errors={iface.crc_errors}, "
                        f"input errors={iface.input_errors}, resets={iface.resets}."
                    ),
                    explanation=(
                        f"CRC/input errors on {iface.name} commonly indicate physical layer issues, "
                        "duplex mismatches, optics/cabling problems, or hardware faults."
                    ),
                    next_commands=[
                        f"show interfaces {iface.name} counters errors",
                        f"show interfaces {iface.name} transceiver",
                        f"show log | include {iface.name}",
                    ],
                )
            )
    return findings


def check_cdp_neighbors(snapshot: DeviceSnapshot) -> list[Finding]:
    """Warn when no CDP neighbors are detected."""
    if snapshot.neighbors:
        return []
    return [
        Finding(
            severity=FindingSeverity.WARNING,
            category="neighbors",
            title="No CDP neighbors detected",
            detail=(
                "The 'show cdp neighbors' output returned no neighbor entries. "
                "CDP may be disabled or this node may have no adjacent Cisco devices."
            ),
            explanation="If neighbors are expected, verify CDP state and link health on relevant interfaces.",
            next_commands=[
                "show cdp",
                "show cdp interface",
                "show cdp neighbors detail",
            ],
        )
    ]


def check_routing(snapshot: DeviceSnapshot) -> list[Finding]:
    """Create routing findings from normalized route entries."""
    findings: list[Finding] = []
    has_default, counts = _route_stats(snapshot.routes)

    if not has_default:
        findings.append(
            Finding(
                severity=FindingSeverity.CRITICAL,
                category="routing",
                title="No default route in routing table",
                detail=(
                    "The routing table does not contain a default route (0.0.0.0/0). "
                    "Traffic to unknown destinations will be dropped."
                ),
                explanation=(
                    "Without a default route, this device cannot forward packets to destinations not "
                    "explicitly listed in its routing table."
                ),
                next_commands=[
                    "show ip route 0.0.0.0",
                    "show ip bgp summary",
                    "show ip ospf neighbor",
                    "show ip eigrp neighbors",
                    "show run | include ip route",
                ],
            )
        )

    if counts:
        protocol_summary = ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))
        findings.append(
            Finding(
                severity=FindingSeverity.INFO,
                category="routing",
                title="Routing table summary",
                detail=f"Route type distribution: {protocol_summary}",
                explanation=(
                    "The routing table contains one or more route families. Review the distribution "
                    "to confirm it matches your expected topology."
                ),
                next_commands=[
                    "show ip route summary",
                    "show ip ospf database" if "O" in counts else "show ip route static",
                ],
            )
        )

    return findings


def get_rule_registry() -> list[Rule]:
    """Return the ordered deterministic rule registry."""
    return [
        check_interfaces_down,
        check_admin_down,
        check_err_disabled,
        check_interface_errors,
        check_cdp_neighbors,
        check_routing,
    ]


def evaluate_snapshot(snapshot: DeviceSnapshot) -> list[Finding]:
    """Evaluate all registered rules and return sorted findings."""
    findings: list[Finding] = []
    for rule in get_rule_registry():
        findings.extend(rule(snapshot))

    severity_order = {
        FindingSeverity.CRITICAL: 0,
        FindingSeverity.WARNING: 1,
        FindingSeverity.INFO: 2,
        FindingSeverity.OK: 3,
    }
    findings.sort(key=lambda finding: severity_order.get(finding.severity, 99))
    return findings
