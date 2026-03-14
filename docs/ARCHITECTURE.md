# MindNet Architecture

MindNet is a local-first network diagnostics CLI. It collects operational device state, normalizes that data into a snapshot, evaluates deterministic rules, and then formats the results for terminal use.

## Simple Diagram

```text
Operator Request
      |
      v
CLI Layer
      |
      v
Connector Resolution
      |
      v
SSH / API Collection
      |
      v
Snapshot Model
      |
      v
Rule Engine
      |
      v
Formatter / Explanation Layer
```

The central design rule is that deterministic collection and rules define the product’s truth. Explanation layers can summarize or enrich findings, but they should not replace the collected evidence.

## CLI Layer

The Typer-based CLI in `src/netmind/cli.py` is the operator-facing entrypoint.

Responsibilities:

- parse commands and options
- load environment defaults
- build device profiles
- route requests into connectors, collectors, snapshots, and formatters
- keep the operator workflow local and terminal-first

## Connector Resolution

Connectors abstract how MindNet talks to a target.

Current scope:

- SSH connectors for device command collection
- API connector abstraction for future expansion
- saved connector metadata with secret resolution from the local credential store

This allows the CLI and analysis layers to stay decoupled from transport details.

## SSH / API Collection

Collection is responsible for:

- connectivity validation
- single-command execution
- audit bundle collection
- mock-mode fallback for local testing

Collection should stay narrow and explicit. MindNet is not trying to become a generic automation runtime.

## Snapshot Model

The snapshot model converts raw command outputs into structured Python models.

Current normalized entities include:

- interfaces
- routes
- neighbors
- raw command outputs

Snapshots make it possible to analyze a device without re-reading ad hoc text blobs everywhere in the codebase.

## Rule Engine

The deterministic rule engine evaluates snapshots and produces typed findings.

Examples include:

- unexpected interfaces down
- administratively down interfaces
- err-disabled ports
- interface error counters
- missing default route
- absent CDP neighbors

This layer is the basis for trust in MindNet. It is testable, reviewable, and independent of optional AI features.

## Formatter / Explanation Layer

The formatter layer turns findings and raw outputs into operator-friendly terminal output.

Responsibilities:

- present connectivity and command results
- summarize findings
- explain likely meaning in plain language
- suggest useful next commands

Any future AI-assisted explanation should build on snapshot and rule outputs rather than bypass them.

## Security And Local State

MindNet stores connector metadata locally and keeps secrets in the OS keyring. It is intentionally local-first and avoids outbound telemetry by default.

See [../SECURITY.md](../SECURITY.md) for the security model.

## Current Source Layout

The repository already has a clean, package-oriented structure:

- `src/netmind/cli.py`
- `src/netmind/connectors/`
- `src/netmind/security/`
- `src/netmind/audit.py`
- `src/netmind/explain.py`
- `src/netmind/rules.py`
- `src/netmind/models.py`
- `src/netmind/formatters.py`
- `src/netmind/snapshot_store.py`

That structure is appropriate for the project’s current size and should remain the default until a concrete scaling need appears.
