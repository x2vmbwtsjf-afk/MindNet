"""
MindNet terminal formatters.

All Rich-based terminal rendering lives here.  CLI commands call these
functions to display results — keeping presentation separate from logic.

Design notes:
  - Every public function accepts a Rich Console as first argument so that
    callers can pass a test console (e.g., Console(record=True)) if needed.
  - Colors and icons follow practical terminal conventions: green=good,
    red=bad, yellow=warning, cyan=informational.
"""

from datetime import datetime, timezone

from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich import box

from .models import AuditFinding, AuditReport, FindingSeverity
from .version import __app_name__, __version__


# ---------------------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------------------

_SEVERITY_STYLE: dict[FindingSeverity, str] = {
    FindingSeverity.CRITICAL: "bold red",
    FindingSeverity.WARNING:  "bold yellow",
    FindingSeverity.INFO:     "cyan",
    FindingSeverity.OK:       "bold green",
}

_SEVERITY_ICON: dict[FindingSeverity, str] = {
    FindingSeverity.CRITICAL: "✖",
    FindingSeverity.WARNING:  "▲",
    FindingSeverity.INFO:     "●",
    FindingSeverity.OK:       "✔",
}


def _severity_text(severity: FindingSeverity) -> Text:
    icon = _SEVERITY_ICON.get(severity, "?")
    label = severity.value.upper()
    style = _SEVERITY_STYLE.get(severity, "white")
    return Text(f"{icon} {label}", style=style)


# ---------------------------------------------------------------------------
# Banner / header
# ---------------------------------------------------------------------------

def print_banner(console: Console) -> None:
    """Print the MindNet banner."""
    banner = Text()
    banner.append("  MindNet ", style="bold cyan")
    banner.append(f"v{__version__}", style="dim cyan")
    banner.append("  —  ", style="dim white")
    banner.append("AI Infrastructure Brain", style="italic white")
    console.print(Panel(banner, border_style="cyan", padding=(0, 2)))


def print_product_overview(console: Console) -> None:
    """Print a concise product-style landing view for the CLI."""
    print_banner(console)
    console.print()
    console.print(
        Panel(
            "[bold white]MindNet[/bold white] is a local-first infrastructure intelligence console.\n"
            "It helps you inspect live targets, analyze saved CLI evidence, and build\n"
            "operational context before moving toward execution.",
            title="[bold cyan]Overview[/bold cyan]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    workflows = Table(box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan")
    workflows.add_column("Workflow", style="bold white")
    workflows.add_column("Use It For")
    workflows.add_column("Command")
    workflows.add_row("Live access", "Connectivity checks and direct device inspection", "mindnet connect <target>")
    workflows.add_row("Diagnostics", "Structured audit with findings and next steps", "mindnet audit <target>")
    workflows.add_row("Offline analysis", "Reason about pasted or saved CLI output", "mindnet explain-output")
    workflows.add_row("Saved context", "Re-run analysis on structured evidence", "mindnet snapshot analyze <path>")
    console.print(workflows)
    console.print()

    console.print("[bold cyan]Quick start[/bold cyan]")
    console.print("  [green]1.[/green] export NETMIND_MOCK=true")
    console.print("  [green]2.[/green] mindnet audit 10.0.0.1")
    console.print("  [green]3.[/green] cat mock_data/show__ip__route.txt | mindnet explain-output")
    console.print("  [green]4.[/green] mindnet shell")
    console.print()
    console.print("[dim]Run `mindnet --help` for the full command surface.[/dim]")


def print_version(console: Console) -> None:
    """Print version info."""
    console.print(f"[bold cyan]{__app_name__}[/bold cyan] version [green]{__version__}[/green]")
    console.print("[dim]AI Infrastructure Brain[/dim]")


# ---------------------------------------------------------------------------
# Connection status
# ---------------------------------------------------------------------------

def print_connect_result(console: Console, host: str, success: bool, message: str) -> None:
    """Print the result of a connectivity test."""
    if success:
        console.print(f"[bold green]✔  Connected:[/bold green] [white]{host}[/white]")
        console.print(f"   [dim]{message}[/dim]")
    else:
        console.print(f"[bold red]✖  Connection failed:[/bold red] [white]{host}[/white]")
        console.print(f"   [red]{message}[/red]")


def print_operation_banner(console: Console, title: str, subtitle: str) -> None:
    """Print a compact product-style banner for command execution flows."""
    console.print()
    console.print(
        Panel(
            f"[bold white]{title}[/bold white]\n[dim]{subtitle}[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )


# ---------------------------------------------------------------------------
# Single command output
# ---------------------------------------------------------------------------

def print_command_output(
    console: Console,
    host: str,
    command: str,
    output: str,
    explanation: dict | None = None,
) -> None:
    """
    Print raw command output in a clean framed block.

    Optionally appends a plain-language explanation and next-command hints
    when the `explanation` dict is provided (from explain.explain_command_output).
    """
    console.print()
    console.print(Rule(f"[cyan]{host}[/cyan]  [dim]#[/dim]  [white]{command}[/white]", style="dim"))
    console.print()
    console.print(output.strip())
    console.print()

    if explanation:
        console.print(Rule("[bold]MindNet Analysis[/bold]", style="cyan"))
        console.print()
        console.print(f"[bold cyan]Summary:[/bold cyan]  {explanation.get('summary', '')}")
        next_cmds = explanation.get("next_commands", [])
        if next_cmds:
            console.print()
            console.print("[bold cyan]Recommended next commands:[/bold cyan]")
            for cmd in next_cmds:
                console.print(f"  [green]→[/green]  [white]{cmd}[/white]")
        console.print()


def print_offline_analysis(
    console: Console,
    source_name: str,
    command: str,
    output: str,
    explanation: dict,
    findings: list[AuditFinding],
) -> None:
    """Render offline analysis for pasted or file-based CLI output."""
    print_command_output(
        console,
        host=source_name,
        command=command,
        output=output,
        explanation=explanation,
    )
    if not findings:
        console.print(Panel(
            "[bold green]✔  No deterministic issues detected for this output.[/bold green]",
            border_style="green",
            padding=(0, 2),
        ))
        return

    console.print(Rule("[bold]Findings[/bold]", style="cyan"))
    for idx, finding in enumerate(findings, start=1):
        print_finding(console, finding, idx)


# ---------------------------------------------------------------------------
# Audit report
# ---------------------------------------------------------------------------

def print_audit_header(console: Console, report: AuditReport) -> None:
    """Print the audit report header with host, timestamp, and summary counts."""
    console.print()
    console.print(
        Panel(
            f"[bold white]Audit Report[/bold white]\n"
            f"[dim]Host:[/dim]      [cyan]{report.host}[/cyan]\n"
            f"[dim]Timestamp:[/dim] [white]{report.timestamp}[/white]\n"
            f"[dim]Commands:[/dim]  [white]{len(report.raw_outputs)}[/white]",
            title="[bold cyan]MindNet[/bold cyan]",
            border_style="cyan",
            padding=(0, 2),
        )
    )


def print_audit_summary(console: Console, report: AuditReport) -> None:
    """Print a one-line summary of finding counts by severity."""
    c = report.critical_count
    w = report.warning_count
    i = report.info_count

    console.print()
    console.print(
        f"  [bold red]✖ {c} Critical[/bold red]   "
        f"[bold yellow]▲ {w} Warning[/bold yellow]   "
        f"[cyan]● {i} Info[/cyan]"
    )
    console.print()


def print_finding(console: Console, finding: AuditFinding, index: int) -> None:
    """Print a single AuditFinding in a structured block."""
    severity_txt = _severity_text(finding.severity)
    style = _SEVERITY_STYLE.get(finding.severity, "white")

    console.print(Rule(style=style))

    # Title line
    console.print(
        Text.assemble(
            (f"  [{index}] ", "dim white"),
            severity_txt,
            ("  ", ""),
            (finding.title, "bold white"),
        )
    )
    console.print(f"  [dim]Category: {finding.category}[/dim]")
    console.print()

    # Detail
    console.print(f"  [bold]Detail:[/bold]  {finding.detail}")
    console.print()

    # Explanation
    console.print(f"  [bold cyan]What this means:[/bold cyan]")
    # Word-wrap the explanation with a left margin
    for line in _wrap_text(finding.explanation, width=80):
        console.print(f"    {line}")
    console.print()

    # Next commands
    if finding.next_commands:
        console.print("  [bold cyan]Recommended next commands:[/bold cyan]")
        for cmd in finding.next_commands:
            console.print(f"    [green]→[/green]  [white]{cmd}[/white]")
    console.print()


def print_audit_report(console: Console, report: AuditReport, show_raw: bool = False) -> None:
    """
    Render the complete audit report to the terminal.

    Args:
        console:  Rich Console to render to.
        report:   AuditReport with findings populated.
        show_raw: If True, also print raw command outputs at the end.
    """
    print_audit_header(console, report)
    print_audit_summary(console, report)

    if not report.findings:
        console.print(
            Panel(
                "[bold green]✔  No issues detected.[/bold green]\n"
                "[dim]All audit checks passed without findings.[/dim]",
                border_style="green",
                padding=(0, 2),
            )
        )
        return

    console.print(Rule("[bold]Findings[/bold]", style="cyan"))

    for idx, finding in enumerate(report.findings, start=1):
        print_finding(console, finding, idx)

    console.print(Rule(style="dim"))
    console.print()

    if show_raw:
        console.print(Rule("[bold]Raw Command Outputs[/bold]", style="dim"))
        for cmd, output in report.raw_outputs.items():
            console.print()
            console.print(f"[bold cyan]# {cmd}[/bold cyan]")
            console.print(output.strip())
            console.print()


def print_status_dashboard(console: Console, report: AuditReport) -> None:
    """Render a compact infrastructure status dashboard from an analyzed report."""
    snapshot = report.snapshot
    interfaces = snapshot.interfaces if snapshot else []
    routes = snapshot.routes if snapshot else []
    neighbors = snapshot.neighbors if snapshot else []
    connected_platforms = sorted({neighbor.platform for neighbor in neighbors if neighbor.platform})
    local_links = sorted({neighbor.local_interface for neighbor in neighbors if neighbor.local_interface})
    snapshot_age = _format_snapshot_age(report.timestamp)

    up_interfaces = sum(1 for iface in interfaces if iface.status.lower() == "up" and iface.protocol.lower() == "up")
    down_interfaces = sum(
        1
        for iface in interfaces
        if "down" in iface.status.lower() and "admin" not in iface.status.lower()
    )
    admin_down = sum(1 for iface in interfaces if "administratively down" in iface.status.lower())
    err_disabled = sum(
        1
        for iface in interfaces
        if "err-disabled" in iface.status.lower() or "err" in iface.switchport_status.lower()
    )
    default_route = any(route.prefix == "0.0.0.0/0" for route in routes)
    route_families = sorted({route.code for route in routes})

    health_score = 100
    health_score -= report.critical_count * 25
    health_score -= report.warning_count * 10
    health_score -= err_disabled * 10
    health_score -= down_interfaces * 5
    if not default_route:
        health_score -= 15
    health_score = max(0, min(100, health_score))

    if health_score < 60:
        health_label = "[bold red]Critical issues detected[/bold red]"
        health_style = "red"
    elif health_score < 85:
        health_label = "[bold yellow]Warnings require review[/bold yellow]"
        health_style = "yellow"
    else:
        health_label = "[bold green]Operationally healthy[/bold green]"
        health_style = "green"

    summary = Table.grid(expand=True)
    summary.add_column(style="cyan", ratio=1)
    summary.add_column(style="white", ratio=2)
    summary.add_row("Host", report.host)
    summary.add_row("Timestamp", report.timestamp)
    summary.add_row("Snapshot age", snapshot_age)
    summary.add_row("Health", health_label)
    summary.add_row("Health score", f"{health_score}/100")
    summary.add_row("Commands", str(len(report.raw_outputs)))
    summary.add_row("Route families", ", ".join(route_families) if route_families else "None")

    interfaces_table = Table.grid(expand=True)
    interfaces_table.add_column(style="cyan", ratio=1)
    interfaces_table.add_column(justify="right", style="bold white", ratio=1)
    interfaces_table.add_row("Up", str(up_interfaces))
    interfaces_table.add_row("Unexpected down", str(down_interfaces))
    interfaces_table.add_row("Admin down", str(admin_down))
    interfaces_table.add_row("Err-disabled", str(err_disabled))

    routing_table = Table.grid(expand=True)
    routing_table.add_column(style="cyan", ratio=1)
    routing_table.add_column(justify="right", style="bold white", ratio=1)
    routing_table.add_row("Routes", str(len(routes)))
    routing_table.add_row("Default route", "Present" if default_route else "Missing")
    routing_table.add_row("Neighbors", str(len(neighbors)))
    routing_table.add_row("Observed platforms", ", ".join(connected_platforms[:2]) if connected_platforms else "None")
    routing_table.add_row("Findings", str(len(report.findings)))

    topology_table = Table.grid(expand=True)
    topology_table.add_column(style="cyan", ratio=1)
    topology_table.add_column(style="white", ratio=2)
    topology_table.add_row("Connected devices", str(len(neighbors)))
    topology_table.add_row("Connected links", str(len(local_links)))
    topology_table.add_row("Platforms/modules", ", ".join(connected_platforms) if connected_platforms else "Unknown")
    topology_table.add_row("Snapshot source", "Live audit bundle")

    findings_breakdown = Table.grid(expand=True)
    findings_breakdown.add_column(style="cyan", ratio=1)
    findings_breakdown.add_column(justify="right", style="bold white", ratio=1)
    findings_breakdown.add_row("Critical", str(report.critical_count))
    findings_breakdown.add_row("Warning", str(report.warning_count))
    findings_breakdown.add_row("Info", str(report.info_count))
    findings_breakdown.add_row(
        "Top severity",
        "CRITICAL" if report.critical_count else "WARNING" if report.warning_count else "INFO",
    )

    findings_table = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold cyan",
        expand=True,
    )
    findings_table.add_column("Severity", width=10)
    findings_table.add_column("Title")

    if report.findings:
        for finding in report.findings[:5]:
            findings_table.add_row(_severity_text(finding.severity), finding.title)
    else:
        findings_table.add_row("[bold green]OK[/bold green]", "No deterministic issues detected")

    interfaces_focus = Table(
        box=box.SIMPLE_HEAVY,
        show_header=True,
        header_style="bold cyan",
        expand=True,
    )
    interfaces_focus.add_column("Interface", style="bold white")
    interfaces_focus.add_column("Status")
    interfaces_focus.add_column("Signal", justify="right")

    ranked_interfaces = sorted(
        interfaces,
        key=lambda iface: (
            0 if "err" in iface.switchport_status.lower() or "err-disabled" in iface.status.lower() else
            1 if iface.crc_errors > 0 or iface.input_errors > 0 else
            2 if "down" in iface.status.lower() and "admin" not in iface.status.lower() else
            3
        ),
    )

    for iface in ranked_interfaces[:4]:
        if iface.switchport_status:
            status = iface.switchport_status
        elif iface.status and iface.protocol:
            status = f"{iface.status}/{iface.protocol}"
        else:
            status = iface.status or "unknown"

        if iface.crc_errors or iface.input_errors:
            signal = f"CRC {iface.crc_errors}, IN {iface.input_errors}"
        elif iface.switchport_status:
            signal = iface.switchport_status
        else:
            signal = "stable"

        interfaces_focus.add_row(iface.name, status, signal)

    if not ranked_interfaces:
        interfaces_focus.add_row("n/a", "No interfaces", "No data")

    next_actions = Table.grid(expand=True)
    next_actions.add_column(style="bold white")
    next_actions.add_column(style="green")
    suggested_commands: list[str] = []
    for finding in report.findings:
        for command in finding.next_commands:
            if command not in suggested_commands:
                suggested_commands.append(command)
            if len(suggested_commands) >= 4:
                break
        if len(suggested_commands) >= 4:
            break

    if suggested_commands:
        for idx, command in enumerate(suggested_commands, start=1):
            next_actions.add_row(f"{idx}.", command)
    else:
        next_actions.add_row("1.", "No immediate follow-up commands suggested")

    console.print()
    console.print(
        Panel(
            f"[bold white]Infrastructure Status[/bold white]\n[dim]Live snapshot rendered as a compact CLI dashboard.[/dim]",
            border_style="cyan",
            padding=(0, 2),
        )
    )
    console.print()
    console.print(
        Columns(
            [
                Panel(summary, title="[bold cyan]Summary[/bold cyan]", border_style=health_style, padding=(0, 1)),
                Panel(interfaces_table, title="[bold cyan]Interfaces[/bold cyan]", border_style="cyan", padding=(0, 1)),
                Panel(routing_table, title="[bold cyan]Routing[/bold cyan]", border_style="cyan", padding=(0, 1)),
                Panel(topology_table, title="[bold cyan]Topology Context[/bold cyan]", border_style="cyan", padding=(0, 1)),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print()
    console.print(
        Columns(
            [
                Panel(findings_breakdown, title="[bold cyan]Findings Breakdown[/bold cyan]", border_style="cyan", padding=(0, 1)),
                Panel(interfaces_focus, title="[bold cyan]Interface Spotlight[/bold cyan]", border_style="cyan", padding=(0, 1)),
            ],
            equal=True,
            expand=True,
        )
    )
    console.print()
    console.print(
        Columns(
            [
                Panel(findings_table, title="[bold cyan]Top Findings[/bold cyan]", border_style="cyan", padding=(0, 1)),
                Panel(next_actions, title="[bold cyan]Recommended Actions[/bold cyan]", border_style="green", padding=(0, 1)),
            ],
            equal=True,
            expand=True,
        )
    )


def print_error(console: Console, message: str) -> None:
    """Print a prominent error message."""
    console.print(f"[bold red]Error:[/bold red] {message}")


def print_success(console: Console, message: str) -> None:
    """Print a success message."""
    console.print(f"[bold green]✔[/bold green]  {message}")


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _wrap_text(text: str, width: int = 80) -> list[str]:
    """Naive word-wrap that avoids pulling in textwrap for simple use cases."""
    import textwrap
    return textwrap.wrap(text, width=width)


def _format_snapshot_age(timestamp: str) -> str:
    """Return a compact human-readable age for an ISO snapshot timestamp."""
    try:
        snapshot_time = datetime.fromisoformat(timestamp)
    except ValueError:
        return "Unknown"

    if snapshot_time.tzinfo is None:
        snapshot_time = snapshot_time.replace(tzinfo=timezone.utc)

    delta = datetime.now(timezone.utc) - snapshot_time.astimezone(timezone.utc)
    total_seconds = max(0, int(delta.total_seconds()))
    if total_seconds < 60:
        return f"{total_seconds}s ago"
    if total_seconds < 3600:
        return f"{total_seconds // 60}m ago"
    if total_seconds < 86400:
        return f"{total_seconds // 3600}h ago"
    return f"{total_seconds // 86400}d ago"
