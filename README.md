# MindNet

**AI Infrastructure Brain**

MindNet is a local-first CLI for infrastructure analysis. It connects to network
devices over SSH, collects operational state, turns raw command output into a
structured snapshot, and explains what to check next.

MindNet is intentionally local and terminal-first:
- no web UI
- no SaaS control plane
- no database requirement
- no outbound telemetry by default

The current package path remains `netmind` for compatibility, but the product
name and primary CLI command are `MindNet` and `mindnet`.

## Current Status

MindNet is at an early but usable MVP stage.

Implemented today:
- `connect` for connectivity validation
- `run` for single-command execution
- `audit` for deterministic device analysis
- `explain-output` for pasted offline CLI analysis
- `analyze-file` for saved offline CLI output analysis
- `snapshot export/show/analyze`
- `connector add/list/show/remove`
- secure local credential storage via OS keyring
- local interactive shell
- full mock mode for offline development

## Installation

Requirements:
- Python 3.11+
- a working virtual environment
- OS keyring support if you want saved connector secrets

```bash
git clone https://github.com/x2vmbwtsjf-afk/mindnet.git
cd mindnet

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
pip install -e .
```

Optional isolated install with `pipx`:

```bash
pipx install .
```

Install directly from GitHub with `pipx`:

```bash
pipx install git+https://github.com/x2vmbwtsjf-afk/mindnet.git
```

Verify:

```bash
mindnet version
```

Compatibility note:

```bash
netmind version
```

Both commands work. `mindnet` is the preferred command name.

MindNet is intended to be used as an installed CLI product. The supported entry
paths are `mindnet` and the compatibility alias `netmind`, not `python main.py`.

## Quick Start

### Mock mode

```bash
export NETMIND_MOCK=true

mindnet connect 10.0.0.1
mindnet run 10.0.0.1 "show version"
mindnet audit 10.0.0.1
mindnet snapshot export 10.0.0.1 /tmp/mindnet-snapshot.json
mindnet snapshot analyze /tmp/mindnet-snapshot.json
```

MindNet includes built-in mock responses and can also read command-specific
files from `mock_data/*.txt`.

Example:
- `mock_data/show__ip__route.txt` maps to `show ip route`

### Live device

```bash
mindnet connect 192.168.1.1 --username admin --password 'secret'

export NETMIND_USERNAME=admin
export NETMIND_PASSWORD='secret'
mindnet audit 192.168.1.1
```

MindNet loads `.env` automatically through `python-dotenv`.

### Offline analysis

MindNet can analyze pasted or saved CLI outputs without a live device session.

```bash
mindnet analyze-file mock_data/show__ip__route.txt
mindnet analyze-file --type interfaces-status mock_data/show__interfaces__status.txt
cat mock_data/show__cdp__neighbors.txt | mindnet explain-output
```

## CLI Commands

### `mindnet version`

Print version and product descriptor.

### `mindnet connect <target>`

Validate connectivity only.

`<target>` can be:
- a host or IP address
- a saved connector name

Examples:

```bash
mindnet connect 192.168.1.1 --username admin --password 'secret'
mindnet connect lab-core-1
```

### `mindnet run <host> "<command>"`

Run one command and print:
- raw output
- plain-language summary
- recommended next commands

Example:

```bash
mindnet run 192.168.1.1 "show ip interface brief"
```

### `mindnet audit <host>`

Run the built-in audit bundle, collect a `DeviceSnapshot`, evaluate findings,
and print explanations and next steps.

Example:

```bash
mindnet audit 192.168.1.1
mindnet audit 192.168.1.1 --raw
```

Exit codes:
- `0`: success, no critical findings
- `1`: connection or execution failure
- `2`: audit completed with critical findings

### `mindnet explain-output`

Analyze pasted CLI output from standard input.

Supported offline types:
- `ip-int-brief`
- `interfaces-status`
- `ip-route`
- `cdp-neighbors`

Examples:

```bash
cat mock_data/show__ip__route.txt | mindnet explain-output
cat mock_data/show__interfaces__status.txt | mindnet explain-output --type interfaces-status
```

### `mindnet analyze-file <path>`

Analyze saved CLI output from a file.

Examples:

```bash
mindnet analyze-file mock_data/show__ip__interface__brief.txt
mindnet analyze-file --type cdp-neighbors mock_data/show__cdp__neighbors.txt
```

### `mindnet shell`

Start the local interactive shell.

The shell is local-only and intended for safe demos and UX workflows.

### `mindnet snapshot export <host> <path>`

Run collectors and save a structured snapshot as JSON.

### `mindnet snapshot show <path>`

Print a short summary of a saved snapshot.

### `mindnet snapshot analyze <path>`

Load a saved snapshot and run the same deterministic rule engine used by
`audit`.

## Connector Management

MindNet supports saved connectors with local metadata plus OS-managed secrets.

### `mindnet connector add`

Prompts for:
- connector name
- connector type
- host
- platform
- username
- password or token

Sensitive values are stored in the OS keyring, not in project files.

### `mindnet connector list`

Lists saved connector metadata without exposing secrets.

### `mindnet connector show <name>`

Shows connector metadata only.

### `mindnet connector remove <name>`

Removes connector metadata and deletes the associated keyring secret.

## Security Model

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

Backends used through the `keyring` library:
- macOS Keychain
- Windows Credential Manager
- Linux Secret Service

## Architecture

The production CLI lives under `src/netmind/`.

Core modules:
- `src/netmind/cli.py`: Typer command layer
- `src/netmind/connectors/`: connector abstraction and transport backends
- `src/netmind/security/`: config metadata plus keyring secret handling
- `src/netmind/audit.py`: collection workflow
- `src/netmind/explain.py`: parsing and explanation logic
- `src/netmind/rules.py`: deterministic finding engine
- `src/netmind/models.py`: typed models including `DeviceSnapshot`
- `src/netmind/formatters.py`: Rich terminal rendering
- `src/netmind/mock_device.py`: offline development path

## Audit Bundle

The default audit currently collects:
- `show version`
- `show ip interface brief`
- `show interfaces status`
- `show cdp neighbors`
- `show ip route`
- `show interfaces`

The outputs are parsed into:
- interfaces
- routes
- neighbors
- findings

## Development

Run checks:

```bash
source .venv/bin/activate
export PYTHONPATH=src
python -m compileall src tests
pytest -q
```

Mock smoke:

```bash
export NETMIND_MOCK=true
mindnet connect 10.0.0.1
mindnet run 10.0.0.1 "show ip route"
mindnet audit 10.0.0.1
```

Verification note:
- `python -m compileall src tests netmind` completed successfully in this environment.
- If `pytest` is flaky in your current shell environment, document that explicitly
  instead of claiming full verification.

Future packaging note:
- A standalone binary build can be added later with PyInstaller.
- That is not part of the current release flow.

## Project Layout

```text
netmind/
├── AGENT.md
├── README.md
├── ROADMAP.md
├── LICENSE
├── pyproject.toml
├── requirements.txt
├── mock_data/
├── src/
│   └── netmind/
│       ├── cli.py
│       ├── audit.py
│       ├── explain.py
│       ├── rules.py
│       ├── models.py
│       ├── formatters.py
│       ├── ssh_client.py
│       ├── snapshot_store.py
│       ├── mock_device.py
│       ├── connectors/
│       └── security/
└── tests/
```

## Roadmap

High-level phases:
1. CLI MVP
2. Snapshot model
3. Rule engine
4. Fabric collection
5. Simulation
6. AI explanation

See [ROADMAP.md](ROADMAP.md) for details.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT
