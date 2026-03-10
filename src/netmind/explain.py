"""
MindNet explain engine.

This module converts raw CLI output into structured models and deterministic findings.
It is the main analysis layer used by audit and single-command explain paths.
"""

from __future__ import annotations

from datetime import datetime, timezone
import re

from .models import (
    AuditReport,
    DeviceSnapshot,
    Finding,
    Interface,
    Neighbor,
    Route,
)
from .rules import (
    check_admin_down,
    check_cdp_neighbors,
    check_err_disabled,
    check_interfaces_down,
    check_routing,
    evaluate_snapshot,
)


_OUTPUT_TYPE_COMMANDS = {
    "ip-int-brief": "show ip interface brief",
    "interfaces-status": "show interfaces status",
    "ip-route": "show ip route",
    "cdp-neighbors": "show cdp neighbors",
}


def _parse_ip_interface_brief(output: str) -> list[Interface]:
    """Parse `show ip interface brief` output into Interface models."""
    interfaces: list[Interface] = []
    for line in output.strip().splitlines():
        if not line.strip() or line.startswith("Interface"):
            continue
        parts = line.split()
        if len(parts) < 6:
            continue
        interfaces.append(
            Interface(
                name=parts[0],
                ip_address=parts[1],
                status=" ".join(parts[4:-1]),
                protocol=parts[-1],
            )
        )
    return interfaces


def _parse_interfaces_status(output: str) -> list[Interface]:
    """Parse `show interfaces status` output into Interface models."""
    interfaces: list[Interface] = []
    for line in output.strip().splitlines():
        if not line.strip() or line.startswith("Port"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        interfaces.append(Interface(name=parts[0], switchport_status=parts[2]))
    return interfaces


def _parse_cdp_neighbors(output: str) -> list[Neighbor]:
    """Parse `show cdp neighbors` output into Neighbor models."""
    neighbors: list[Neighbor] = []
    in_table = False
    for line in output.splitlines():
        if line.startswith("Device ID"):
            in_table = True
            continue
        if not in_table or not line.strip() or line.startswith("Total"):
            continue
        parts = line.split()
        device_id = parts[0]
        local_interface = ""
        platform = ""
        remote_interface = ""
        if len(parts) >= 3:
            local_interface = f"{parts[1]} {parts[2]}"
        if len(parts) >= 6:
            platform = parts[-2]
        if len(parts) >= 1:
            remote_interface = parts[-1]

        neighbors.append(
            Neighbor(
                device_id=device_id,
                local_interface=local_interface,
                remote_interface=remote_interface,
                platform=platform,
            )
        )
    return neighbors


def _parse_route_table(output: str) -> list[Route]:
    """Parse `show ip route` output into Route models."""
    routes: list[Route] = []
    known_route_codes = {
        "L", "C", "S", "R", "M", "B", "D", "EX", "O", "IA",
        "N1", "N2", "E1", "E2", "i", "su", "L1", "L2", "ia",
        "U", "o", "P", "H", "l", "a",
    }

    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("Codes:") or stripped.startswith("Gateway of last resort"):
            continue

        prefix_match = re.search(r"(\d+\.\d+\.\d+\.\d+\/\d+)", stripped)
        if not prefix_match:
            continue

        first_token = re.sub(r"[*+%]", "", stripped.split()[0])
        if first_token not in known_route_codes:
            continue

        prefix = prefix_match.group(1)

        next_hop_match = re.search(r"via\s+(\d+\.\d+\.\d+\.\d+)", stripped)
        next_hop = next_hop_match.group(1) if next_hop_match else ""

        out_if = ""
        if "," in stripped:
            out_if = stripped.split(",")[-1].strip()

        routes.append(
            Route(
                code=first_token,
                prefix=prefix,
                next_hop=next_hop,
                outgoing_interface=out_if,
                raw=stripped,
            )
        )
    return routes


def _parse_interfaces_detail(output: str) -> list[Interface]:
    """Parse `show interfaces` counters/states into Interface models."""
    interfaces: list[Interface] = []
    current: Interface | None = None

    for line in output.splitlines():
        m = re.match(r"^(\S+) is (.*?)(?:,|$)", line)
        if m:
            if current:
                interfaces.append(current)
            current = Interface(name=m.group(1), status=m.group(2).strip().lower())
            continue

        if not current:
            continue

        crc_m = re.search(r"CRC:\s*(\d+)", line)
        if crc_m:
            current.crc_errors = int(crc_m.group(1))

        ie_m = re.search(r"Input errors:\s*(\d+)", line)
        if ie_m:
            current.input_errors = int(ie_m.group(1))

        rst_m = re.search(r"interface resets:\s*(\d+)", line)
        if rst_m:
            current.resets = int(rst_m.group(1))

    if current:
        interfaces.append(current)

    return interfaces


def _merge_interfaces(*collections: list[Interface]) -> list[Interface]:
    """Merge interface fragments from multiple parser sources by name."""
    merged: dict[str, Interface] = {}
    for interfaces in collections:
        for iface in interfaces:
            if iface.name not in merged:
                merged[iface.name] = Interface(name=iface.name)
            item = merged[iface.name]

            if iface.ip_address:
                item.ip_address = iface.ip_address
            if iface.status:
                item.status = iface.status
            if iface.protocol:
                item.protocol = iface.protocol
            if iface.switchport_status:
                item.switchport_status = iface.switchport_status

            item.crc_errors = max(item.crc_errors, iface.crc_errors)
            item.input_errors = max(item.input_errors, iface.input_errors)
            item.resets = max(item.resets, iface.resets)

    return list(merged.values())


def build_snapshot(host: str, timestamp: str, raw_outputs: dict[str, str]) -> DeviceSnapshot:
    """Build a DeviceSnapshot from raw command outputs."""
    ip_brief = []
    if_status = []
    if_detail = []
    routes: list[Route] = []
    neighbors: list[Neighbor] = []

    ip_brief_output = raw_outputs.get("show ip interface brief", "")
    if ip_brief_output and not ip_brief_output.startswith("[ERROR]"):
        ip_brief = _parse_ip_interface_brief(ip_brief_output)

    if_status_output = raw_outputs.get("show interfaces status", "")
    if if_status_output and not if_status_output.startswith("[ERROR]"):
        if_status = _parse_interfaces_status(if_status_output)

    if_detail_output = raw_outputs.get("show interfaces", "")
    if if_detail_output and not if_detail_output.startswith("[ERROR]"):
        if_detail = _parse_interfaces_detail(if_detail_output)

    route_output = raw_outputs.get("show ip route", "")
    if route_output and not route_output.startswith("[ERROR]"):
        routes = _parse_route_table(route_output)

    cdp_output = raw_outputs.get("show cdp neighbors", "")
    if cdp_output and not cdp_output.startswith("[ERROR]"):
        neighbors = _parse_cdp_neighbors(cdp_output)

    interfaces = _merge_interfaces(ip_brief, if_status, if_detail)

    return DeviceSnapshot(
        host=host,
        timestamp=timestamp,
        interfaces=interfaces,
        routes=routes,
        neighbors=neighbors,
        raw_outputs=raw_outputs,
    )


def _route_stats(routes: list[Route]) -> tuple[bool, dict[str, int]]:
    """Return route health stats from normalized routes for single-command explain."""
    has_default = any(route.prefix == "0.0.0.0/0" for route in routes)
    protocol_counts: dict[str, int] = {}
    for route in routes:
        protocol_counts[route.code] = protocol_counts.get(route.code, 0) + 1
    return has_default, protocol_counts


def findings_from_snapshot(snapshot: DeviceSnapshot) -> list[Finding]:
    """Run deterministic checks against a DeviceSnapshot via rule registry."""
    return evaluate_snapshot(snapshot)


def analyze_report(report: AuditReport) -> AuditReport:
    """Populate report snapshot/findings using snapshot-based analysis."""
    if report.snapshot is None:
        report.snapshot = build_snapshot(report.host, report.timestamp, report.raw_outputs)

    report.findings = findings_from_snapshot(report.snapshot)
    return report


def detect_command_type(output: str) -> str | None:
    """Best-effort detection of supported offline CLI output types."""
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    if not lines:
        return None

    first = lines[0].strip().lower()
    normalized = "\n".join(line.lower() for line in lines[:4])

    if first.startswith("interface") and "ip-address" in first and "protocol" in first:
        return "ip-int-brief"
    if first.startswith("port") and "status" in first and "vlan" in first:
        return "interfaces-status"
    if first.startswith("device id") and "platform" in first and "port id" in first:
        return "cdp-neighbors"
    if "codes:" in first or "gateway of last resort" in normalized:
        return "ip-route"
    return None


def resolve_command_name(command_type: str) -> str:
    """Resolve a supported offline analysis type to its canonical command."""
    key = command_type.strip().lower()
    if key not in _OUTPUT_TYPE_COMMANDS:
        supported = ", ".join(sorted(_OUTPUT_TYPE_COMMANDS))
        raise ValueError(f"Unsupported analysis type '{command_type}'. Supported types: {supported}")
    return _OUTPUT_TYPE_COMMANDS[key]


def offline_analysis_types() -> list[str]:
    """Return supported offline analysis type keys."""
    return sorted(_OUTPUT_TYPE_COMMANDS)


def analyze_offline_output(
    output: str,
    command_type: str | None = None,
    source_name: str = "offline-input",
) -> tuple[str, DeviceSnapshot, list[Finding], dict]:
    """Analyze pasted or file-based CLI output without a live device session."""
    resolved_type = command_type or detect_command_type(output)
    if resolved_type is None:
        supported = ", ".join(offline_analysis_types())
        raise ValueError(
            "Could not detect command type from input. "
            f"Pass --type explicitly. Supported types: {supported}"
        )

    command = resolve_command_name(resolved_type)
    timestamp = datetime.now(timezone.utc).isoformat()
    snapshot = build_snapshot(source_name, timestamp, {command: output})
    findings = _findings_for_command(command, snapshot)
    explanation = explain_command_output(command, output)
    return command, snapshot, findings, explanation


def _findings_for_command(command: str, snapshot: DeviceSnapshot) -> list[Finding]:
    """Run only the rule subset that is valid for a partial single-command snapshot."""
    cmd = command.strip().lower()
    if cmd == "show ip interface brief":
        return _sort_findings(check_interfaces_down(snapshot) + check_admin_down(snapshot))
    if cmd == "show interfaces status":
        return _sort_findings(check_err_disabled(snapshot))
    if cmd == "show ip route":
        return _sort_findings(check_routing(snapshot))
    if cmd == "show cdp neighbors":
        return _sort_findings(check_cdp_neighbors(snapshot))
    return []


def _sort_findings(findings: list[Finding]) -> list[Finding]:
    """Sort findings with the same severity order used by the rule engine."""
    severity_order = {
        "critical": 0,
        "warning": 1,
        "info": 2,
        "ok": 3,
    }
    findings.sort(key=lambda finding: severity_order.get(finding.severity.value, 99))
    return findings


def explain_command_output(command: str, output: str) -> dict:
    """Generate plain-language explanation for a single command output."""
    cmd = command.strip().lower()

    if "show version" in cmd:
        return {
            "summary": (
                "This output shows device software version, platform details, uptime, and image metadata. "
                "Validate uptime and confirm the software release is approved for your environment."
            ),
            "next_commands": [
                "show processes cpu history",
                "show processes memory sorted",
                "show log",
            ],
        }

    if "show ip interface brief" in cmd:
        interfaces = _parse_ip_interface_brief(output)
        down = [iface.name for iface in interfaces if "down" in iface.status.lower() and "admin" not in iface.status.lower()]
        summary = f"Parsed {len(interfaces)} interfaces."
        if down:
            summary += f" The following are unexpectedly down: {', '.join(down)}."
        else:
            summary += " All non-admin-down interfaces appear to be up."

        return {
            "summary": summary,
            "next_commands": [
                "show interfaces",
                "show log | include GigabitEthernet",
            ],
        }

    if "show ip route" in cmd:
        routes = _parse_route_table(output)
        has_default, protocol_counts = _route_stats(routes)
        default_status = "A default route is present." if has_default else "WARNING: No default route found."
        return {
            "summary": f"{default_status} Route protocol distribution: {protocol_counts}",
            "next_commands": [
                "show ip route summary",
                "show ip bgp summary",
                "show ip ospf neighbor",
            ],
        }

    if "show interfaces status" in cmd:
        interfaces = _parse_interfaces_status(output)
        err_disabled = [iface.name for iface in interfaces if "err-disabled" in iface.switchport_status.lower()]
        connected = [iface.name for iface in interfaces if iface.switchport_status.lower() == "connected"]
        summary = f"Parsed {len(interfaces)} switchport entries."
        if err_disabled:
            summary += f" Err-disabled ports detected: {', '.join(err_disabled)}."
        elif connected:
            summary += f" Connected ports detected: {len(connected)}."
        return {
            "summary": summary,
            "next_commands": [
                "show interfaces status",
                "show errdisable recovery",
                "show log",
            ],
        }

    if "show cdp neighbors" in cmd:
        neighbors = _parse_cdp_neighbors(output)
        if neighbors:
            names = ", ".join(neighbor.device_id for neighbor in neighbors)
            return {
                "summary": f"Found {len(neighbors)} CDP neighbor(s): {names}.",
                "next_commands": [
                    "show cdp neighbors detail",
                    "show lldp neighbors",
                ],
            }
        return {
            "summary": "No CDP neighbors found. Verify CDP is enabled and links are operational.",
            "next_commands": [
                "show cdp",
                "show cdp interface",
            ],
        }

    line_count = len([line for line in output.splitlines() if line.strip()])
    return {
        "summary": f"Command returned {line_count} lines of output. Review above for relevant details.",
        "next_commands": [
            "show log",
            "show running-config",
        ],
    }
