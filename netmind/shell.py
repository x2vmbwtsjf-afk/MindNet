"""Interactive CLI shell for MindNet built on prompt_toolkit."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import FileHistory

from commands.audit import handle_audit
from commands.connect import handle_connect
from commands.health import handle_show_health
from commands.run import handle_run


@dataclass(frozen=True)
class Command:
    """Represents a shell command in the registry."""

    name: str
    usage: str
    description: str
    handler: Callable[[list[str]], None]


class RegistryCompleter(Completer):
    """Tab completion based on command registry."""

    def __init__(self, command_names: list[str]) -> None:
        self._command_names = sorted(command_names)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lstrip()
        if not text:
            for cmd in self._command_names:
                yield Completion(cmd, start_position=0)
            return

        words = text.split()
        if text.endswith(" "):
            words.append("")

        if len(words) == 1:
            prefix = words[0]
            for cmd in self._command_names:
                if cmd.startswith(prefix):
                    yield Completion(cmd, start_position=-len(prefix))
            return

        if len(words) == 2 and words[0] == "show":
            prefix = words[1]
            if "health".startswith(prefix):
                yield Completion("health", start_position=-len(prefix))


class NetMindShell:
    """MindNet interactive shell with command registry and history."""

    def __init__(self) -> None:
        self._registry = self._build_registry()
        history_path = Path(__file__).resolve().parent / ".mindnet_history"
        self._session = PromptSession(
            message="mindnet> ",
            completer=RegistryCompleter(list(self._registry.keys())),
            history=FileHistory(str(history_path)),
        )

    def run(self) -> None:
        """Start the shell REPL loop."""
        print("MindNet interactive shell")
        print("Type 'help' to list commands. Type 'exit' to quit.")

        while True:
            try:
                raw = self._session.prompt()
            except (KeyboardInterrupt, EOFError):
                print("\nBye.")
                break

            line = raw.strip()
            if not line:
                continue

            try:
                args = shlex.split(line)
            except ValueError as exc:
                print(f"Error: invalid input ({exc})")
                continue

            if args[0] in {"exit", "quit"}:
                print("Bye.")
                break

            if args[0] == "help":
                self._print_help()
                continue

            command_name, command_args = self._resolve_command(args)
            if command_name is None:
                print(f"Unknown command: {line}")
                print("Type 'help' to see available commands.")
                continue

            self._registry[command_name].handler(command_args)

    def _resolve_command(self, args: list[str]) -> tuple[str | None, list[str]]:
        """Resolve the command name from input arguments."""
        if len(args) >= 2 and args[0] == "show" and args[1] == "health":
            return "show health", args[2:]

        if args[0] in self._registry:
            return args[0], args[1:]

        return None, []

    def _print_help(self) -> None:
        """Print command help from the registry."""
        print("Available commands:")
        for name in sorted(self._registry.keys()):
            cmd = self._registry[name]
            print(f"  {cmd.usage:<22} {cmd.description}")
        print("  help                   Show this help message")
        print("  exit                   Exit shell")

    @staticmethod
    def _build_registry() -> dict[str, Command]:
        """Build command registry."""
        return {
            "connect": Command(
                name="connect",
                usage="connect <ip>",
                description="Placeholder: test connection to a device",
                handler=handle_connect,
            ),
            "run": Command(
                name="run",
                usage="run <command>",
                description="Placeholder: execute a network command",
                handler=handle_run,
            ),
            "audit": Command(
                name="audit",
                usage="audit",
                description="Run local mock audit output",
                handler=handle_audit,
            ),
            "show health": Command(
                name="show health",
                usage="show health",
                description="Show local shell health status",
                handler=handle_show_health,
            ),
        }
