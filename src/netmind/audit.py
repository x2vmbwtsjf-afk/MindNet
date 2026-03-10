"""
MindNet audit engine.

Defines the audit command bundle and orchestrates collection of all outputs
from the target device.  Parsing and analysis live in explain.py — this
module is only responsible for fetching data.

Keeping collection and analysis separate makes it easy to:
  - Add new commands to the bundle without touching analysis logic
  - Replay audit data from saved files (future feature)
  - Unit-test analysis independently of live SSH
"""

from datetime import datetime, timezone

from .models import AuditReport, CommandResult, DeviceProfile
from .ssh_client import run_commands
from . import explain


# ---------------------------------------------------------------------------
# Audit command bundle
# Edit this list to add or remove commands from the standard audit.
# Order matters — commands run in the sequence listed.
# ---------------------------------------------------------------------------

AUDIT_COMMANDS: list[str] = [
    "show version",
    "show ip interface brief",
    "show interfaces status",
    "show cdp neighbors",
    "show ip route",
    "show interfaces",
]


def run_audit(profile: DeviceProfile) -> AuditReport:
    """
    Execute the full audit command bundle against the target device.

    Collects raw output for every command in AUDIT_COMMANDS and packages
    them into an AuditReport ready for analysis by the explain module.

    Args:
        profile: DeviceProfile with SSH connection parameters.

    Returns:
        AuditReport containing raw outputs and an empty findings list.
        Callers should pass this to explain.analyze_report() to populate
        the findings.
    """
    timestamp = datetime.now(timezone.utc).isoformat()

    results: list[CommandResult] = run_commands(profile, AUDIT_COMMANDS)

    raw_outputs: dict[str, str] = {}
    for result in results:
        if result.success:
            raw_outputs[result.command] = result.output
        else:
            # Store the error so the explain layer can note it
            raw_outputs[result.command] = f"[ERROR] {result.error_msg}"

    report = AuditReport(
        host=profile.host,
        timestamp=timestamp,
        raw_outputs=raw_outputs,
        findings=[],
    )

    # Parse outputs into a structured snapshot and run deterministic findings.
    report.snapshot = explain.build_snapshot(report.host, report.timestamp, report.raw_outputs)
    report.findings = explain.findings_from_snapshot(report.snapshot)
    return report
