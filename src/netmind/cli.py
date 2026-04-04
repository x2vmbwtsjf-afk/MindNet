"""
MindNet CLI entry point.

Defines all user-facing commands using Typer.
Each command is a thin orchestrator:
  1. Build DeviceProfile from args / env
  2. Call the appropriate module (ssh_client, audit, explain)
  3. Pass results to formatters for display

Commands:
  mindnet version            — Print version info
  mindnet connect <ip>       — Test SSH connectivity
  mindnet run <ip> <command> — Execute a single command
  mindnet audit <ip>         — Run full audit bundle and display findings
  mindnet shell              — Start the local interactive shell
  mindnet snapshot ...       — Export or inspect local snapshots
"""

import os
import sys

import typer
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv

from .models import AuditReport, DeviceProfile, DeviceType
from . import ssh_client, audit as audit_module, explain, formatters
from .security.credentials import CredentialStore
from .snapshot_store import load_snapshot, save_snapshot
from .shell import NetMindShell


app = typer.Typer(
    name="mindnet",
    help="MindNet — AI Infrastructure Brain.",
    add_completion=False,
    pretty_exceptions_enable=False,
)
snapshot_app = typer.Typer(help="Export and inspect structured device snapshots.")
connector_app = typer.Typer(help="Manage saved connector profiles.")
app.add_typer(snapshot_app, name="snapshot")
app.add_typer(connector_app, name="connector")

console = Console()
load_dotenv()


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    """Render a product-style landing view when MindNet is invoked without a subcommand."""
    if ctx.resilient_parsing:
        return
    if ctx.invoked_subcommand is None:
        formatters.print_product_overview(console)


# ---------------------------------------------------------------------------
# Shared option factory
# Typer doesn't support reusable option groups natively, so we define
# common options inline on each command.  For MVP this is acceptable.
# ---------------------------------------------------------------------------

def _build_profile(
    host: str,
    username: str,
    password: str,
    port: int,
    device_type: str,
    secret: str,
    timeout: int,
) -> DeviceProfile:
    """Construct a DeviceProfile, with env-var fallbacks for credentials."""
    return DeviceProfile(
        host=host,
        username=username or os.environ.get("NETMIND_USERNAME", ""),
        password=password or os.environ.get("NETMIND_PASSWORD", ""),
        port=port,
        device_type=device_type,
        secret=secret or os.environ.get("NETMIND_SECRET", ""),
        timeout=timeout,
    )


def _get_credential_store() -> CredentialStore:
    """Return the credential store service used by connector commands."""
    return CredentialStore()


def _build_profile_from_saved_connector(name: str, timeout: int) -> DeviceProfile | None:
    """Load a saved connector profile and resolve its secret from keyring."""
    saved = _get_credential_store().load_connector_credentials(name)
    if saved is None:
        return None
    return DeviceProfile(
        host=saved.host,
        username=saved.username,
        password=saved.secret or "",
        device_type=saved.platform or DeviceType.CISCO_IOS,
        connector_type=saved.connector_type or "ssh",
        timeout=timeout,
    )


def _is_mock_mode() -> bool:
    """Return True when NETMIND_MOCK is set to a truthy value."""
    return os.environ.get("NETMIND_MOCK", "").strip().lower() in {"1", "true", "yes", "on"}


def _require_credentials(profile: DeviceProfile) -> None:
    """Exit with a helpful message if username or password are missing."""
    if not profile.username:
        console.print(
            "[bold red]Error:[/bold red] Username is required.\n"
            "  Pass [cyan]--username[/cyan] or set [cyan]NETMIND_USERNAME[/cyan] in your environment."
        )
        raise typer.Exit(code=1)
    if not profile.password:
        console.print(
            "[bold red]Error:[/bold red] Password is required.\n"
            "  Pass [cyan]--password[/cyan] or set [cyan]NETMIND_PASSWORD[/cyan] in your environment.\n"
            "  Tip: set [cyan]NETMIND_MOCK=true[/cyan] to test without a real device."
        )
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

@app.command()
def version() -> None:
    """Print MindNet version information."""
    formatters.print_banner(console)
    console.print()
    formatters.print_version(console)


# ---------------------------------------------------------------------------
# connect
# ---------------------------------------------------------------------------

@app.command()
def connect(
    host: str = typer.Argument(..., help="Device IP address, hostname, or saved connector name"),
    username: str = typer.Option("", "--username", "-u", help="SSH username (or set NETMIND_USERNAME)"),
    password: str = typer.Option("", "--password", "-p", help="SSH password (or set NETMIND_PASSWORD)", hide_input=True),
    port: int = typer.Option(22, "--port", help="SSH port"),
    device_type: str = typer.Option(DeviceType.CISCO_IOS, "--device-type", "-d", help="Netmiko device type"),
    secret: str = typer.Option("", "--secret", "-s", help="Enable secret (Cisco)", hide_input=True),
    timeout: int = typer.Option(30, "--timeout", "-t", help="Connection timeout in seconds"),
) -> None:
    """
    Test SSH connectivity to a network device.

    Attempts an SSH handshake and reports success or failure.
    No commands are run.  Use this to verify credentials before auditing.

    \b
    Examples:
      mindnet connect 192.168.1.1 -u admin -p cisco
      NETMIND_MOCK=true mindnet connect 10.0.0.1
    """
    profile = _build_profile_from_saved_connector(host, timeout)
    display_target = host
    if profile is None:
        profile = _build_profile(host, username, password, port, device_type, secret, timeout)
    else:
        display_target = profile.host

    if not _is_mock_mode():
        _require_credentials(profile)

    formatters.print_operation_banner(
        console,
        "Connectivity Check",
        "Validate transport access before running diagnostics or collection.",
    )
    console.print(
        f"[dim]Connecting to[/dim] [cyan]{display_target}:{profile.port}[/cyan] [dim]...[/dim]"
    )

    success, message = ssh_client.test_connectivity(profile)
    formatters.print_connect_result(console, display_target, success, message)

    raise typer.Exit(code=0 if success else 1)


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

@app.command()
def run(
    host: str = typer.Argument(..., help="Device IP address or hostname"),
    command: str = typer.Argument(..., help='CLI command to execute, e.g. "show version"'),
    username: str = typer.Option("", "--username", "-u", help="SSH username"),
    password: str = typer.Option("", "--password", "-p", help="SSH password", hide_input=True),
    port: int = typer.Option(22, "--port", help="SSH port"),
    device_type: str = typer.Option(DeviceType.CISCO_IOS, "--device-type", "-d"),
    secret: str = typer.Option("", "--secret", "-s", hide_input=True),
    timeout: int = typer.Option(30, "--timeout", "-t"),
    explain_output: bool = typer.Option(True, "--explain/--no-explain", help="Show plain-English explanation"),
) -> None:
    """
    Execute a single CLI command on a device and display the output.

    MindNet will also print a plain-English explanation of what the output
    means and suggest follow-up commands (use --no-explain to suppress this).

    \b
    Examples:
      mindnet run 192.168.1.1 "show version" -u admin -p cisco
      mindnet run 192.168.1.1 "show ip interface brief" -u admin -p cisco
      NETMIND_MOCK=true mindnet run 10.0.0.1 "show ip route"
    """
    profile = _build_profile(host, username, password, port, device_type, secret, timeout)

    if not _is_mock_mode():
        _require_credentials(profile)

    formatters.print_operation_banner(
        console,
        "Command Execution",
        "Capture raw device output and attach deterministic explanation.",
    )
    console.print(f"[dim]Running on[/dim] [cyan]{host}[/cyan]: [white]{command}[/white]")

    result = ssh_client.run_command(profile, command)

    if not result.success:
        formatters.print_error(console, f"Command failed: {result.error_msg}")
        raise typer.Exit(code=1)

    explanation_data = None
    if explain_output:
        explanation_data = explain.explain_command_output(command, result.output)

    formatters.print_command_output(
        console,
        host=host,
        command=command,
        output=result.output,
        explanation=explanation_data,
    )


# ---------------------------------------------------------------------------
# audit
# ---------------------------------------------------------------------------

@app.command()
def audit(
    host: str = typer.Argument(..., help="Device IP address or hostname"),
    username: str = typer.Option("", "--username", "-u", help="SSH username"),
    password: str = typer.Option("", "--password", "-p", help="SSH password", hide_input=True),
    port: int = typer.Option(22, "--port", help="SSH port"),
    device_type: str = typer.Option(DeviceType.CISCO_IOS, "--device-type", "-d"),
    secret: str = typer.Option("", "--secret", "-s", hide_input=True),
    timeout: int = typer.Option(30, "--timeout", "-t"),
    show_raw: bool = typer.Option(False, "--raw", help="Also print raw command outputs"),
) -> None:
    """
    Run a full audit against a network device.

    Executes a predefined bundle of show commands, parses the results,
    identifies potential issues, and provides plain-English explanations
    and recommended next steps for each finding.

    \b
    Audit commands include:
      show version
      show ip interface brief
      show interfaces status
      show cdp neighbors
      show ip route
      show interfaces

    \b
    Examples:
      mindnet audit 192.168.1.1 -u admin -p cisco
      NETMIND_MOCK=true mindnet audit 10.0.0.1
      NETMIND_MOCK=true mindnet audit 10.0.0.1 --raw
    """
    profile = _build_profile(host, username, password, port, device_type, secret, timeout)

    if not _is_mock_mode():
        _require_credentials(profile)

    formatters.print_operation_banner(
        console,
        "Infrastructure Audit",
        "Collect a deterministic evidence bundle and evaluate it for operational risk.",
    )
    console.print(f"[dim]Starting audit on[/dim] [cyan]{host}[/cyan] [dim]...[/dim]")
    console.print(f"[dim]Running {len(audit_module.AUDIT_COMMANDS)} commands[/dim]")
    console.print()

    # Collect outputs
    report = audit_module.run_audit(profile)

    # Analyze and populate findings
    report = explain.analyze_report(report)

    # Render
    formatters.print_audit_report(console, report, show_raw=show_raw)

    # Exit with non-zero code if critical findings exist
    if report.critical_count > 0:
        raise typer.Exit(code=2)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@app.command()
def status(
    host: str = typer.Argument(..., help="Device IP address, hostname, or saved connector name"),
    username: str = typer.Option("", "--username", "-u", help="SSH username"),
    password: str = typer.Option("", "--password", "-p", help="SSH password", hide_input=True),
    port: int = typer.Option(22, "--port", help="SSH port"),
    device_type: str = typer.Option(DeviceType.CISCO_IOS, "--device-type", "-d"),
    secret: str = typer.Option("", "--secret", "-s", hide_input=True),
    timeout: int = typer.Option(30, "--timeout", "-t"),
) -> None:
    """
    Render a compact infrastructure status dashboard for a target.

    This command uses the standard audit collection bundle, then summarizes the
    resulting snapshot into a CLI-native dashboard view.
    """
    profile = _build_profile_from_saved_connector(host, timeout)
    display_target = host
    if profile is None:
        profile = _build_profile(host, username, password, port, device_type, secret, timeout)
    else:
        display_target = profile.host

    if not _is_mock_mode():
        _require_credentials(profile)

    formatters.print_operation_banner(
        console,
        "Infrastructure Status",
        "Collect current evidence and render a compact health dashboard.",
    )
    console.print(f"[dim]Building status view for[/dim] [cyan]{display_target}[/cyan] [dim]...[/dim]")
    console.print(f"[dim]Collecting {len(audit_module.AUDIT_COMMANDS)} commands for the snapshot[/dim]")

    report = audit_module.run_audit(profile)
    report = explain.analyze_report(report)
    formatters.print_status_dashboard(console, report)


# ---------------------------------------------------------------------------
# offline analysis
# ---------------------------------------------------------------------------

@app.command("explain-output")
def explain_output(
    command_type: str = typer.Option(
        "",
        "--type",
        help="Offline input type. Supported: ip-int-brief, interfaces-status, ip-route, cdp-neighbors.",
    ),
) -> None:
    """
    Analyze pasted CLI output from stdin without connecting to a live device.

    Example:
      cat output.txt | mindnet explain-output --type ip-route
    """
    if sys.stdin.isatty():
        formatters.print_error(
            console,
            "No stdin content detected. Pipe CLI output into this command or use analyze-file.",
        )
        raise typer.Exit(code=1)

    output = sys.stdin.read()
    if not output.strip():
        formatters.print_error(console, "Received empty stdin input.")
        raise typer.Exit(code=1)

    formatters.print_operation_banner(
        console,
        "Offline Output Analysis",
        "Interpret pasted CLI evidence without needing live device access.",
    )

    try:
        command, _snapshot, findings, explanation_data = explain.analyze_offline_output(
            output=output,
            command_type=command_type or None,
            source_name="stdin",
        )
    except ValueError as exc:
        formatters.print_error(console, str(exc))
        raise typer.Exit(code=1)

    formatters.print_offline_analysis(
        console,
        source_name="stdin",
        command=command,
        output=output,
        explanation=explanation_data,
        findings=findings,
    )


@app.command("analyze-file")
def analyze_file(
    path: str = typer.Argument(..., help="Path to a text file with saved CLI output"),
    command_type: str = typer.Option(
        "",
        "--type",
        help="Offline input type. Supported: ip-int-brief, interfaces-status, ip-route, cdp-neighbors.",
    ),
) -> None:
    """
    Analyze saved CLI output from a text file without requiring live SSH access.

    Example:
      mindnet analyze-file --type interfaces-status samples/interfaces-status.txt
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            output = handle.read()
    except OSError as exc:
        formatters.print_error(console, f"Failed to read input file: {exc}")
        raise typer.Exit(code=1)

    if not output.strip():
        formatters.print_error(console, "Input file is empty.")
        raise typer.Exit(code=1)

    formatters.print_operation_banner(
        console,
        "Offline File Analysis",
        "Interpret saved CLI evidence and produce findings, context, and next steps.",
    )

    try:
        command, _snapshot, findings, explanation_data = explain.analyze_offline_output(
            output=output,
            command_type=command_type or None,
            source_name=path,
        )
    except ValueError as exc:
        formatters.print_error(console, str(exc))
        raise typer.Exit(code=1)

    formatters.print_offline_analysis(
        console,
        source_name=path,
        command=command,
        output=output,
        explanation=explanation_data,
        findings=findings,
    )


# ---------------------------------------------------------------------------
# shell
# ---------------------------------------------------------------------------

@app.command()
def shell() -> None:
    """
    Start the interactive local shell.

    This mode supports command abbreviations, tab completion, and context
    help using '?'. It is fully local and does not require SSH.
    """
    NetMindShell().cmdloop()


# ---------------------------------------------------------------------------
# connector
# ---------------------------------------------------------------------------

@connector_app.command("add")
def connector_add() -> None:
    """Interactively create a saved connector profile."""
    name = typer.prompt("Connector name").strip()
    connector_type = typer.prompt("Connector type", default="ssh").strip().lower()
    host = typer.prompt("Host").strip()
    platform = typer.prompt("Platform", default=DeviceType.CISCO_IOS).strip()
    username = typer.prompt("Username").strip()
    secret = typer.prompt("Password / token", hide_input=True, confirmation_prompt=True)

    _get_credential_store().save_connector_credentials(
        name=name,
        username=username,
        secret=secret,
        host=host,
        platform=platform,
        connector_type=connector_type,
    )
    formatters.print_success(console, f"Connector '{name}' saved")


@connector_app.command("list")
def connector_list() -> None:
    """List saved connector profiles without exposing secrets."""
    records = _get_credential_store().list_connectors()
    if not records:
        console.print("[dim]No saved connectors.[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Host")
    table.add_column("Platform")
    table.add_column("Username")

    for record in sorted(records, key=lambda item: item.name):
        table.add_row(
            record.name,
            record.connector_type,
            record.host,
            record.platform,
            record.username,
        )

    console.print(table)


@connector_app.command("show")
def connector_show(
    name: str = typer.Argument(..., help="Saved connector name"),
) -> None:
    """Show saved connector metadata without printing secrets."""
    record = _get_credential_store().load_connector_metadata(name)
    if record is None:
        formatters.print_error(console, f"Connector '{name}' not found")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]Name:[/bold cyan] {record.name}")
    console.print(f"[bold cyan]Type:[/bold cyan] {record.connector_type}")
    console.print(f"[bold cyan]Host:[/bold cyan] {record.host}")
    console.print(f"[bold cyan]Platform:[/bold cyan] {record.platform}")
    console.print(f"[bold cyan]Username:[/bold cyan] {record.username}")


@connector_app.command("remove")
def connector_remove(
    name: str = typer.Argument(..., help="Saved connector name"),
) -> None:
    """Remove connector metadata and its stored secret."""
    store = _get_credential_store()
    record = store.load_connector_metadata(name)
    if record is None:
        formatters.print_error(console, f"Connector '{name}' not found")
        raise typer.Exit(code=1)

    store.delete_connector_credentials(name)
    formatters.print_success(console, f"Connector '{name}' removed")


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------

@snapshot_app.command("export")
def snapshot_export(
    host: str = typer.Argument(..., help="Device IP address or hostname"),
    output_path: str = typer.Argument(..., help="Output JSON path"),
    username: str = typer.Option("", "--username", "-u", help="SSH username"),
    password: str = typer.Option("", "--password", "-p", help="SSH password", hide_input=True),
    port: int = typer.Option(22, "--port", help="SSH port"),
    device_type: str = typer.Option(DeviceType.CISCO_IOS, "--device-type", "-d"),
    secret: str = typer.Option("", "--secret", "-s", hide_input=True),
    timeout: int = typer.Option(30, "--timeout", "-t"),
) -> None:
    """Collect an audit and export its structured snapshot to JSON."""
    profile = _build_profile(host, username, password, port, device_type, secret, timeout)

    if not _is_mock_mode():
        _require_credentials(profile)

    report = audit_module.run_audit(profile)
    if report.snapshot is None:
        formatters.print_error(console, "Snapshot generation failed.")
        raise typer.Exit(code=1)

    saved_path = save_snapshot(report.snapshot, output_path)
    formatters.print_success(console, f"Snapshot saved to {saved_path}")


@snapshot_app.command("show")
def snapshot_show(
    snapshot_path: str = typer.Argument(..., help="Path to snapshot JSON"),
) -> None:
    """Load a snapshot JSON file and print a short summary."""
    try:
        snapshot = load_snapshot(snapshot_path)
    except Exception as exc:
        formatters.print_error(console, f"Failed to load snapshot: {exc}")
        raise typer.Exit(code=1)

    console.print(f"[bold cyan]Host:[/bold cyan] {snapshot.host}")
    console.print(f"[bold cyan]Timestamp:[/bold cyan] {snapshot.timestamp}")
    console.print(f"[bold cyan]Schema:[/bold cyan] {snapshot.schema_version}")
    console.print(f"[bold cyan]Interfaces:[/bold cyan] {len(snapshot.interfaces)}")
    console.print(f"[bold cyan]Routes:[/bold cyan] {len(snapshot.routes)}")
    console.print(f"[bold cyan]Neighbors:[/bold cyan] {len(snapshot.neighbors)}")


@snapshot_app.command("analyze")
def snapshot_analyze(
    snapshot_path: str = typer.Argument(..., help="Path to snapshot JSON"),
    show_raw: bool = typer.Option(False, "--raw", help="Also print raw command outputs"),
) -> None:
    """Load a snapshot JSON file and run deterministic findings on it."""
    try:
        snapshot = load_snapshot(snapshot_path)
    except Exception as exc:
        formatters.print_error(console, f"Failed to load snapshot: {exc}")
        raise typer.Exit(code=1)

    report = AuditReport(
        host=snapshot.host,
        timestamp=snapshot.timestamp,
        raw_outputs=snapshot.raw_outputs,
        findings=[],
        snapshot=snapshot,
    )
    report = explain.analyze_report(report)
    formatters.print_audit_report(console, report, show_raw=show_raw)

    if report.critical_count > 0:
        raise typer.Exit(code=2)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entry point registered in pyproject.toml / setup.py."""
    app()


if __name__ == "__main__":
    main()
