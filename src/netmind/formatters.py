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

from rich.console import Console
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
