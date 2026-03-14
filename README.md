# MindNet

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![CI](https://github.com/x2vmbwtsjf-afk/MindNet/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/x2vmbwtsjf-afk/MindNet/actions/workflows/ci.yml)

MindNet is a local-first CLI for infrastructure engineers that connects to network devices, collects operational state, converts raw CLI output into structured snapshots, and explains what to check next.

It is designed for engineers who want a practical troubleshooting tool, not a hosted platform. MindNet stays terminal-first, runs locally, avoids outbound telemetry by default, and keeps deterministic analysis at the center of the product.

The package path remains `netmind` for compatibility, but the product name and primary CLI command are `MindNet` and `mindnet`.

## What Problem MindNet Solves

Network troubleshooting usually starts with raw device commands and a mental checklist. That is effective, but it is repetitive, hard to standardize, and easy to lose context across devices and incidents.

MindNet helps by:

- connecting to devices over SSH
- collecting a known set of operational commands
- normalizing the results into a structured snapshot
- running deterministic checks on the collected state
- returning plain-language summaries and useful next commands

## Who It Is For

- network engineers working on switches and routers
- platform or infra teams responsible for network-adjacent operations
- operators who want local analysis without a SaaS dependency
- teams that want AI-assisted explanation on top of a deterministic core

## Current Stage

MindNet is an early but usable MVP. The core CLI, snapshot model, rule engine, offline analysis paths, connector management, mock mode, and tests are already present. The project is still maturing in documentation, CI, connector breadth, and deeper analysis coverage.

## Features

- local-first CLI with `connect`, `run`, `audit`, `shell`, and snapshot workflows
- deterministic analysis over structured `DeviceSnapshot` data
- offline analysis for pasted or saved command output
- mock mode for demos, development, and safe testing
- connector management with OS keyring-backed secret storage
- SSH and connector abstraction layers for future expansion
- plain-language explanations and recommended next commands

## Architecture Overview

MindNet follows a straightforward local pipeline:

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
Deterministic Rules
      |
      v
Formatter / Explanation Layer
```

The key design choice is that deterministic collection and rules remain the source of truth. Any explanation layer should build on that output, not replace it.

More detail is available in [ARCHITECTURE.md](ARCHITECTURE.md).

## Installation

Requirements:

- Python 3.11+
- a virtual environment
- OS keyring support if you want saved connector secrets

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Optional install with `pipx`:

```bash
pipx install .
```

Verify:

```bash
mindnet version
```

Compatibility alias:

```bash
netmind version
```

## CLI Usage Examples

Mock mode:

```bash
export NETMIND_MOCK=true
mindnet connect 10.0.0.1
mindnet run 10.0.0.1 "show version"
mindnet audit 10.0.0.1
mindnet snapshot export 10.0.0.1 /tmp/mindnet-snapshot.json
mindnet snapshot analyze /tmp/mindnet-snapshot.json
```

Live device:

```bash
mindnet connect 192.168.1.1 --username admin --password 'secret'
mindnet audit 192.168.1.1 --username admin --password 'secret'
```

Offline analysis:

```bash
mindnet analyze-file mock_data/show__ip__route.txt
mindnet analyze-file --type interfaces-status mock_data/show__interfaces__status.txt
cat mock_data/show__cdp__neighbors.txt | mindnet explain-output
```

Connector management:

```bash
mindnet connector add
mindnet connector list
mindnet connector show lab-core-1
mindnet connect lab-core-1
```

## Connectors

MindNet currently supports saved connectors with local metadata and OS-managed secrets.

Stored in local config:

- connector name
- host
- platform
- connector type
- username

Stored in OS keyring only:

- password
- token
- API secret

Backends depend on the `keyring` library and may use macOS Keychain, Windows Credential Manager, or Linux Secret Service depending on the host platform.

## Snapshots And Analysis

The default audit bundle currently collects:

- `show version`
- `show ip interface brief`
- `show interfaces status`
- `show cdp neighbors`
- `show ip route`
- `show interfaces`

Those outputs are normalized into a snapshot that can include:

- interfaces
- routes
- neighbors
- findings

Saved snapshots let you analyze device state later without reconnecting to the original target.

## Security Philosophy

MindNet is intended for observation and explanation, not autonomous remediation.

- local-first is the default operating model
- secrets should live in the OS keyring, not in tracked files
- deterministic rules stay ahead of AI-generated interpretation
- mock mode should remain available for safe demos and tests
- no outbound telemetry is enabled by default

The security model is documented in [SECURITY.md](SECURITY.md).

## Example Troubleshooting Session

```text
$ export NETMIND_MOCK=true
$ mindnet audit 10.0.0.1

Connecting to 10.0.0.1
Collecting audit bundle
Building device snapshot
Evaluating deterministic rules

Critical findings:
  - Port Gi1/0/3 is err-disabled

Recommended next commands:
  - show interfaces Gi1/0/3
  - show port-security interface Gi1/0/3
  - show errdisable recovery
```

## Developer Onboarding

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
mindnet --help
```

More detail is in [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap

MindNet is being developed in six phases:

1. CLI MVP
2. Snapshot model
3. Rule engine
4. Fabric collection
5. Simulation
6. AI explanation

See [ROADMAP.md](ROADMAP.md) for details.

## License

MindNet is released under the MIT License. See [LICENSE](LICENSE).
