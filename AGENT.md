# MindNet Agent Guide

This file is the working contract for AI coding agents operating in this repository.
If there is any conflict between code style preferences and this guide, follow this guide.

## 1) Mission
MindNet is a local, terminal-first infrastructure analysis tool for network engineers.
It wraps Cisco-style workflows and improves operator decisions with deterministic analysis first, then explanation.

## 2) Product Boundaries
### In scope (current)
- Local CLI only (no web UI, no SaaS)
- SSH-driven command workflows
- Lightweight parsing for immediate troubleshooting value
- Plain-language explanations and recommended next commands
- Mock mode for development without live devices

### Out of scope (current)
- Cloud services, remote control planes
- Database persistence as a core requirement
- Heavy orchestration frameworks
- Auto-remediation by default

## 3) Current Runtime Surfaces
There are two CLI surfaces in this repo:

1. Main product CLI in `src/netmind/` (Typer + Rich)
- Commands: `version`, `connect`, `run`, `audit`, `explain-output`, `analyze-file`, `shell`
- Entry points: `mindnet = netmind.cli:main` and `netmind = netmind.cli:main`

2. Local shell prototype in `netmind/` (prompt_toolkit)
- Entry point: `python main.py` inside `netmind/`
- Purpose: rapid interaction UX experiments

When implementing production behavior, prioritize `src/netmind/`.

## 4) Architecture Principles
1. Deterministic logic before AI augmentation.
2. Parsed/structured data before narrative explanations.
3. Small, composable modules over large monoliths.
4. Errors should be explicit and actionable in terminal output.
5. Every major behavior must be testable without live devices.

## 5) Source of Truth by Layer
- CLI orchestration: `src/netmind/cli.py`
- Device access: `src/netmind/ssh_client.py`
- Audit command set: `src/netmind/audit.py`
- Analysis/explanations: `src/netmind/explain.py`
- Presentation: `src/netmind/formatters.py`
- Data contracts: `src/netmind/models.py`
- Offline data path: `src/netmind/mock_device.py` + `mock_data/*.txt`

## 6) Command Contract (MVP)
### `mindnet version`
- Print version and short product descriptor.

### `mindnet connect <ip>`
- Validate connectivity only.
- No config changes, no command execution.
- Return clear success/failure and non-zero exit on failure.

### `mindnet run <ip> "<command>"`
- Execute one command and print raw output.
- Optionally append explanation + next commands.

### `mindnet audit <ip>`
- Execute predefined command bundle.
- Parse outputs into findings with severity.
- Print findings, explanations, and next-command suggestions.
- Exit non-zero when critical findings exist.

### `mindnet explain-output`
- Read CLI output from stdin.
- Analyze supported command output without live device access.
- Print deterministic explanation and recommended next checks.

### `mindnet analyze-file <path>`
- Read saved CLI output from a file.
- Analyze supported command output without live device access.
- Preserve deterministic-first behavior.

### `mindnet shell`
- Start local interactive shell experience.
- Must remain local-only and safe by default.

## 7) Parsing and Analysis Rules
- Keep parsers lightweight and transparent.
- Avoid opaque mega-regex patterns when possible.
- Every finding must include:
  - severity
  - title
  - detail/evidence
  - explanation
  - next commands
- Do not infer high-confidence root cause without evidence.
- Prefer “what to verify next” over absolute claims.

## 8) Mock/Offline Development
- `NETMIND_MOCK=true` must allow full local workflows.
- File-based mock responses in `mock_data/*.txt` should override built-ins.
- Mock path must stay deterministic for tests and demos.

## 9) Coding Standards
- Python 3.11+
- Type hints on public functions and models
- Clear, short docstrings for public modules/functions
- Keep modules focused; avoid cross-layer leakage
- Keep user-visible wording practical and operator-friendly
- Code and code comments must be in English

## 10) Error Handling Standards
- Never swallow exceptions silently.
- Show user-safe error messages in CLI output.
- Preserve technical detail internally where useful for debugging.
- Return appropriate exit codes.

## 11) Security and Safety
- Never log plaintext credentials.
- Never auto-execute remediation commands.
- No destructive network changes without explicit user intent.
- Keep local-first behavior; do not add outbound telemetry by default.

## 12) Testing Expectations
Minimum for meaningful change:
1. Unit tests for parser/analysis changes
2. Mock-mode smoke validation for CLI flows
3. No regression in existing command contracts

Suggested local checks:
- `python -m compileall src`
- `pytest -q` (when test deps are installed)
- `NETMIND_MOCK=true` smoke for `connect/run/audit`

## 13) Dependency Policy
- Prefer minimal dependency footprint.
- New dependency requires clear operational value.
- Keep runtime and dev dependencies clearly separated.

## 14) Documentation Policy
When changing behavior, update docs in the same change:
- `README.md` for user-facing behavior
- This file (`AGENT.md`) when agent workflow/architecture expectations change

## 15) Definition of Done
A task is done when:
1. Behavior works in mock mode
2. Tests or compile checks pass locally
3. CLI output is clear and actionable
4. Relevant docs are updated
5. Change is modular and future-extensible

## 16) Roadmap Guardrails
### v0.2
- Add local AI explanation augmentation on top of deterministic findings.
- Keep parser/rule engine as primary signal.

### v0.3
- Add richer interactive chat mode for troubleshooting sessions.
- Maintain command traceability and reproducibility.

### Future
- Vendor abstraction for Cisco, Arista, Juniper via normalized interfaces.

---
If unsure, choose the simpler local-first implementation that preserves operator trust and debuggability.
