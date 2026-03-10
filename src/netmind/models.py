"""
MindNet data models.

Defines the core data structures used across the application.
These are intentionally simple for MVP — no ORM, no database.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DeviceType(str, Enum):
    """Supported device types for SSH connection profiles."""
    CISCO_IOS = "cisco_ios"
    CISCO_NXOS = "cisco_nxos"
    CISCO_XR = "cisco_xr"
    ARISTA_EOS = "arista_eos"       # v0.3 target
    JUNIPER_JUNOS = "juniper_junos" # v0.3 target
    AUTODETECT = "autodetect"


class FindingSeverity(str, Enum):
    """Severity level for audit findings."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    OK = "ok"


@dataclass
class DeviceProfile:
    """
    Holds SSH connection parameters for a target device.

    Attributes:
        host:       IP address or hostname.
        username:   SSH login username.
        password:   SSH login password.
        port:       SSH port (default 22).
        device_type: Netmiko device type string.
        connector_type: Connection backend identifier.
        timeout:    Connection timeout in seconds.
        secret:     Enable secret for Cisco devices (optional).
    """
    host: str
    username: str
    password: str
    port: int = 22
    device_type: str = DeviceType.CISCO_IOS
    connector_type: str = "ssh"
    timeout: int = 30
    secret: str = ""


@dataclass
class CommandResult:
    """
    Stores the raw output of a single command execution.

    Attributes:
        command:   The command that was sent.
        output:    Raw text output returned by the device.
        success:   Whether the command completed without errors.
        error_msg: Error message if success is False.
    """
    command: str
    output: str
    success: bool = True
    error_msg: str = ""


@dataclass
class Interface:
    """
    Normalized interface model collected from CLI commands.

    Attributes:
        name: Interface name (for example, GigabitEthernet0/1).
        ip_address: IP address if known.
        status: Layer-1/admin textual state from command output.
        protocol: Layer-2/L3 protocol state where available.
        switchport_status: Status from `show interfaces status` (connected, err-disabled, etc).
        crc_errors: CRC counter from `show interfaces`.
        input_errors: Input error counter from `show interfaces`.
        resets: Interface reset counter from `show interfaces`.
    """

    name: str
    ip_address: str = ""
    status: str = ""
    protocol: str = ""
    switchport_status: str = ""
    crc_errors: int = 0
    input_errors: int = 0
    resets: int = 0


@dataclass
class Route:
    """
    Normalized route entry model.

    Attributes:
        code: Route code (for example C, S, O, B, L).
        prefix: Route prefix string.
        next_hop: Next-hop address when present.
        outgoing_interface: Outgoing interface when present.
        raw: Original route line for diagnostics.
    """

    code: str
    prefix: str
    next_hop: str = ""
    outgoing_interface: str = ""
    raw: str = ""


@dataclass
class Neighbor:
    """
    Normalized L2/L3 neighbor model.

    Attributes:
        device_id: Neighbor device identifier.
        local_interface: Local interface facing the neighbor.
        remote_interface: Neighbor-facing port ID.
        platform: Neighbor platform text when available.
    """

    device_id: str
    local_interface: str = ""
    remote_interface: str = ""
    platform: str = ""


@dataclass
class Finding:
    """
    A single finding produced during an audit.

    Attributes:
        severity:    FindingSeverity enum value.
        category:    Short tag for the finding type (e.g. "interface", "routing").
        title:       One-line summary of the finding.
        detail:      Expanded description with evidence from the device.
        explanation: Plain-English explanation of why this matters.
        next_commands: List of recommended follow-up commands.
    """
    severity: FindingSeverity
    category: str
    title: str
    detail: str
    explanation: str
    next_commands: list[str] = field(default_factory=list)


@dataclass
class DeviceSnapshot:
    """
    Structured device state assembled from collected command outputs.

    Attributes:
        host: Device IP/hostname.
        timestamp: Snapshot creation timestamp in ISO format.
        interfaces: Normalized interface list.
        routes: Normalized route list.
        neighbors: Normalized neighbor list.
        raw_outputs: Original command output map used to build this snapshot.
        schema_version: Snapshot schema version for compatibility checks.
    """

    host: str
    timestamp: str
    interfaces: list[Interface] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)
    neighbors: list[Neighbor] = field(default_factory=list)
    raw_outputs: dict[str, str] = field(default_factory=dict)
    schema_version: str = "1"


@dataclass
class AuditReport:
    """
    Aggregated report produced by a full audit run.

    Attributes:
        host:      Target device IP / hostname.
        timestamp: ISO-format timestamp of when audit ran.
        findings:  List of Finding objects.
        raw_outputs: Dict mapping command → raw output string.
    """
    host: str
    timestamp: str
    findings: list[Finding] = field(default_factory=list)
    raw_outputs: dict[str, str] = field(default_factory=dict)
    snapshot: Optional[DeviceSnapshot] = None

    @property
    def critical_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.CRITICAL)

    @property
    def warning_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.WARNING)

    @property
    def info_count(self) -> int:
        return sum(1 for f in self.findings if f.severity == FindingSeverity.INFO)


# Backward-compatible alias for existing imports.
AuditFinding = Finding
