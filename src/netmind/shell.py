"""MindNet interactive shell UX for local infrastructure analysis."""

from __future__ import annotations

import cmd
import shlex
from typing import Dict, List, Tuple


COMMAND_TREE: Dict[str, dict] = {
    "show": {
        "ip": {
            "route": {},
            "interface": {"brief": {}},
            "ospf": {"neighbor": {}, "interface": {"brief": {}}},
            "bgp": {"summary": {}},
        },
        "version": {},
        "status": {},
        "interfaces": {"status": {}},
        "cdp": {"neighbors": {"detail": {}}},
        "running-config": {},
        "topology": {},
        "impact": {},
        "risks": {},
    },
    "connect": {},
    "audit": {},
    "explain-output": {},
    "simulate": {"leaf": {}, "spine": {}},
    "help": {},
    "exit": {},
    "quit": {},
}


MOCK_OUTPUTS = {
    "show version": (
        "Cisco IOS XE Software, Version 17.09.04a\n"
        "Device uptime is 4 weeks, 2 days, 6 hours\n"
        'System image file is "bootflash:packages.conf"\n'
    ),
    "show status": (
        "Infrastructure Status\n"
        "Health score: 72/100\n"
        "Summary: warnings require review\n\n"
        "Signals\n"
        "- Interfaces up: 3\n"
        "- Unexpected down: 0\n"
        "- Err-disabled: 1\n"
        "- Default route: present\n"
        "- Neighbors: 1\n\n"
        "Priority actions\n"
        "- show interfaces status\n"
        "- show errdisable recovery\n"
        "- show cdp neighbors detail\n"
    ),
    "show ip route": (
        "Codes: C - connected, S - static, O - OSPF, B - BGP\n\n"
        "C    10.0.0.0/24 is directly connected, Vlan10\n"
        "O    10.10.10.0/24 [110/2] via 192.168.0.2, 00:00:31, Vlan100\n"
        "B    172.16.20.0/24 [20/0] via 192.168.0.3, 00:00:12\n"
    ),
    "show ip interface brief": (
        "Interface              IP-Address      OK? Method Status                Protocol\n"
        "Vlan10                 10.0.0.1        YES manual up                    up\n"
        "Vlan100                192.168.0.1     YES manual up                    up\n"
        "Gi1/0/24               unassigned      YES unset  administratively down down\n"
        "Lo0                    1.1.1.1         YES manual up                    up\n"
    ),
    "show ip ospf neighbor": (
        "Neighbor ID     Pri   State           Dead Time   Address         Interface\n"
        "2.2.2.2           1   FULL/DR         00:00:37    192.168.0.2     Vlan100\n"
    ),
    "show ip ospf interface brief": (
        "Interface    PID   Area            IP Address/Mask    Cost  State Nbrs F/C\n"
        "Vlan100      1     0               192.168.0.1/24    10    BDR   1/1\n"
    ),
    "show ip bgp summary": (
        "BGP router identifier 1.1.1.1, local AS number 65001\n"
        "Neighbor        V    AS MsgRcvd MsgSent   TblVer  InQ OutQ Up/Down  State/PfxRcd\n"
        "192.168.0.3     4 65002    1542    1550      103    0    0 1d02h    24\n"
    ),
    "show interfaces status": (
        "Port      Name               Status       Vlan       Duplex  Speed Type\n"
        "Gi1/0/1                      connected    10         full    1000  10/100/1000BaseTX\n"
        "Gi1/0/24                     err-disabled 999        auto    auto  10/100/1000BaseTX\n"
    ),
    "show cdp neighbors": (
        "Device ID        Local Intrfce     Holdtme    Capability  Platform  Port ID\n"
        "DIST-2           Gig 1/0/1          153           S I       C9300     Gig 1/0/1\n"
    ),
    "show cdp neighbors detail": (
        "Device ID: DIST-2\n"
        "IP address: 10.10.10.2\n"
        "Platform: cisco C9300, Capabilities: Switch IGMP\n"
        "Interface: Gig1/0/1, Port ID (outgoing port): Gig1/0/1\n"
    ),
    "show topology": (
        "Topology snapshot\n"
        "- Spine1 connected to Leaf1, Leaf2, Leaf3\n"
        "- Spine2 connected to Leaf1, Leaf2, Leaf3\n"
        "- Leaf3 hosts 32 servers across VLANs 110, 120\n"
        "- Storage networks attached: iSCSI-A, iSCSI-B\n"
    ),
    "show impact": (
        "Impact query examples:\n"
        "- what happens if leaf3 goes down\n"
        "- what happens if spine2 goes down\n"
        "- what happens if vlan 120 is removed\n"
    ),
    "show risks": (
        "Detected risks:\n"
        "- Single uplink on Gi1/0/48 to backup firewall\n"
        "- Err-disabled access port Gi1/0/24\n"
        "- No redundant management path for OOB switch\n"
    ),
    "audit": (
        "Findings:\n"
        "- 1 err-disabled port found: Gi1/0/24\n"
        "- 1 administrative down interface: Gi1/0/24\n"
        "- OSPF neighbor present on Vlan100\n"
        "- BGP session established with 192.168.0.3\n\n"
        "Recommended next commands:\n"
        "- show interfaces status\n"
        "- show cdp neighbors detail\n"
        "- show ip ospf interface brief\n"
    ),
}


BANNER = """
╔══════════════════════════════════════════════════════════╗
                         MindNet
                  AI Infrastructure Brain
╚══════════════════════════════════════════════════════════╝

MindNet analyzes servers, networks, and cloud infrastructure
and provides automated diagnostics, recommendations, and actions.

Workflows
- Inspect live infrastructure context
- Analyze saved CLI evidence offline
- Review deterministic findings and risks
- Simulate impact across key network nodes

Quick start
- connect <device>
- audit
- show topology
- help

Type 'help' to see available commands.
Type 'connect <device>' to begin.
"""


def tokenize(line: str) -> List[str]:
    """Tokenize user input in a CLI-friendly way."""
    try:
        return shlex.split(line)
    except ValueError:
        return line.strip().split()


class ParseError(Exception):
    """Base parser exception."""


class AmbiguousCommand(ParseError):
    """Raised when an abbreviation matches multiple command tokens."""

    def __init__(self, token: str, matches: List[str]):
        self.token = token
        self.matches = matches
        super().__init__(f"Ambiguous input '{token}': {', '.join(matches)}")


class InvalidCommand(ParseError):
    """Raised when a token does not match command tree options."""


class NetMindShell(cmd.Cmd):
    """Interactive local shell with product-oriented UX."""

    intro = BANNER
    prompt = "mindnet> "
    ruler = "-"

    def default(self, line: str) -> None:
        line = line.strip()
        if not line:
            return
        if line.endswith("?"):
            self._handle_question_mark(line[:-1].rstrip())
            return
        try:
            normalized, subtree = self._resolve_command(line)
            self._execute(normalized, subtree)
        except ParseError as exc:
            print(f"% {exc}")

    def emptyline(self) -> bool:
        return False

    def do_exit(self, arg: str) -> bool:
        print("Bye.")
        return True

    def do_quit(self, arg: str) -> bool:
        return self.do_exit(arg)

    def do_EOF(self, arg: str) -> bool:  # noqa: N802 (cmd module convention)
        print()
        return self.do_exit(arg)

    def do_help(self, arg: str) -> None:
        print("MindNet shell reference")
        print()
        print("Session Workflow")
        print("  connect <device>       Open a local analysis context for a target")
        print("  audit                  Run the built-in diagnostics bundle")
        print("  explain-output         Use the main CLI for pasted offline evidence")
        print()
        print("Context and Analysis")
        print("  show status            View the compact infrastructure status dashboard")
        print("  show version           Inspect platform software and uptime details")
        print("  show topology          View the current infrastructure topology snapshot")
        print("  show impact            Explore example impact questions")
        print("  show risks             View detected infrastructure risks")
        print("  show ip route          Inspect routing state")
        print("  show interfaces status Inspect switchport operational state")
        print()
        print("Simulation")
        print("  simulate leaf <id>     Simulate a leaf-node failure scenario")
        print("  simulate spine <id>    Simulate a spine-node failure scenario")
        print()
        print("Utilities")
        print("  help                   Show this help message")
        print("  exit | quit            Exit MindNet")
        print()
        print("Shortcuts")
        print("  sh ip rou")
        print("  sh ip int br")
        print("  sh cdp nei det")
        print("  sh ?")

    def completenames(self, text: str, *ignored) -> List[str]:
        commands = list(COMMAND_TREE.keys())
        return [entry for entry in commands if entry.startswith(text)]

    def completedefault(self, text: str, line: str, begidx: int, endidx: int) -> List[str]:
        before = line[:begidx]
        tokens = tokenize(before)
        if line.endswith(" ") and not text:
            tokens = tokenize(line)

        try:
            subtree = self._resolve_subtree_for_completion(tokens)
        except ParseError:
            return []

        options = sorted(subtree.keys()) if isinstance(subtree, dict) else []
        return [opt for opt in options if opt.startswith(text)]

    def _resolve_subtree_for_completion(self, tokens: List[str]) -> dict:
        subtree = COMMAND_TREE
        for token in tokens:
            if not token:
                continue
            key = self._match_token(token, subtree)
            subtree = subtree[key]
        return subtree

    def _resolve_command(self, line: str) -> Tuple[str, dict]:
        tokens = tokenize(line)
        if not tokens:
            raise InvalidCommand("Empty command")

        subtree = COMMAND_TREE
        resolved: List[str] = []

        for idx, token in enumerate(tokens):
            if not isinstance(subtree, dict):
                raise InvalidCommand(f"Unexpected token '{token}'")
            if not subtree:
                tail = " ".join(tokens[idx:])
                resolved_line = " ".join(resolved)
                if resolved_line in {"connect", "run", "simulate leaf", "simulate spine"}:
                    return f"{resolved_line} {tail}".strip(), {}
                raise InvalidCommand(f"Unexpected token '{token}'")
            key = self._match_token(token, subtree)
            resolved.append(key)
            subtree = subtree[key]

        return " ".join(resolved), subtree

    def _match_token(self, token: str, subtree: dict) -> str:
        matches = [key for key in subtree.keys() if key.startswith(token)]
        if not matches:
            raise InvalidCommand(f"Invalid input detected at '^' marker: {token}")
        if len(matches) > 1:
            if token in matches:
                return token
            raise AmbiguousCommand(token, sorted(matches))
        return matches[0]

    def _handle_question_mark(self, prefix: str) -> None:
        tokens = tokenize(prefix)
        try:
            subtree = self._resolve_subtree_for_completion(tokens)
        except ParseError as exc:
            print(f"% {exc}")
            return

        options = sorted(subtree.keys())
        if not options:
            print("<cr>")
            return
        for option in options:
            print(option)

    def _execute(self, normalized: str, subtree: dict) -> None:
        if normalized == "show":
            print("% Incomplete command.")
            return

        if normalized.startswith("connect "):
            target = normalized.split(" ", 1)[1]
            print(f"Establishing analysis context for {target} ...")
            print("MindNet session ready")
            print("Mode: local mock infrastructure context")
            print("Status: connected")
            self.prompt = self._build_prompt(target)
            return

        if normalized == "connect":
            print("% Incomplete command. Usage: connect <device>")
            return

        if normalized == "audit":
            print(MOCK_OUTPUTS["audit"])
            return

        if normalized == "explain-output":
            print("Use `mindnet explain-output` from the main CLI to analyze pasted evidence.")
            return

        if normalized.startswith("simulate leaf"):
            leaf_id = normalized.split()[-1] if len(normalized.split()) > 2 else "3"
            print(f"Impact detected for leaf{leaf_id} failure (mock):")
            print("- 32 servers affected")
            print("- 2 storage networks impacted")
            print("- ECMP reroute via Spine2")
            print("- No packet loss expected")
            return

        if normalized.startswith("simulate spine"):
            spine_id = normalized.split()[-1] if len(normalized.split()) > 2 else "2"
            print(f"Impact detected for spine{spine_id} failure (mock):")
            print("- East-west traffic rerouted through alternate spine")
            print("- Reduced redundancy until recovery")
            print("- No immediate outage expected")
            return

        if normalized in MOCK_OUTPUTS:
            print(MOCK_OUTPUTS[normalized])
            return

        if normalized in {"help", "?"}:
            self.do_help("")
            return

        print(f"Executed (mock): {normalized}")

    def _build_prompt(self, target: str) -> str:
        """Build a context-aware shell prompt from the requested target."""
        label = target.strip().lower()
        if not label:
            return "mindnet:connected> "
        if any(character.isalpha() for character in label):
            return f"mindnet:{label}> "
        return "mindnet:connected> "
