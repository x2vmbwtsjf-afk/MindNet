"""
MindNet SSH client compatibility layer.

The CLI and audit flows still import this module, but connection handling now
goes through the connector abstraction in `netmind.connectors`.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from .connectors.manager import get_connector, open_connector
from .models import CommandResult, DeviceProfile


def test_connectivity(profile: DeviceProfile) -> tuple[bool, str]:
    """Attempt connectivity using the resolved connector backend."""
    return get_connector(profile).test_connectivity()


@contextmanager
def open_connection(profile: DeviceProfile) -> Generator:
    """
    Yield an active connector session.

    The returned object exposes `run_command()` and `close()`.
    """
    with open_connector(profile) as connector:
        yield connector


def run_command(profile: DeviceProfile, command: str) -> CommandResult:
    """Execute a single command using the resolved connector."""
    try:
        with open_connection(profile) as connector:
            output = connector.run_command(command)
            return CommandResult(command=command, output=output, success=True)
    except Exception as exc:
        return CommandResult(command=command, output="", success=False, error_msg=str(exc))


def run_commands(profile: DeviceProfile, commands: list[str]) -> list[CommandResult]:
    """Execute multiple commands in one connector session."""
    results: list[CommandResult] = []

    try:
        with open_connection(profile) as connector:
            for command in commands:
                try:
                    output = connector.run_command(command)
                    results.append(CommandResult(command=command, output=output, success=True))
                except Exception as exc:
                    results.append(
                        CommandResult(command=command, output="", success=False, error_msg=str(exc))
                    )
    except Exception as exc:
        for command in commands[len(results):]:
            results.append(
                CommandResult(command=command, output="", success=False, error_msg=str(exc))
            )

    return results
