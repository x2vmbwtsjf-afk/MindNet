# MindNet Security Model

MindNet is designed as a local operator tool for network diagnostics and analysis. Its security posture is based on minimizing exposure, keeping secrets out of source-controlled files, and preserving a deterministic core for analysis.

## Core Principles

- local-first by default
- no outbound telemetry by default
- secrets stored in the OS keyring when possible
- deterministic rules as the source of truth
- no autonomous remediation by default

## Credential Handling

MindNet supports saved connectors with:

- metadata stored locally
- secrets stored through the host OS keyring backend

This reduces the need to keep passwords or API tokens in shell history or project files.

Recommended practice:

- prefer saved connectors or environment variables over inline secrets
- avoid committing `.env` files or raw device credentials
- use mock mode for demos, tests, and screenshots

## Local State

MindNet intentionally avoids introducing a hosted control plane or a mandatory external database.

Local state may include:

- connector metadata
- exported snapshots
- mock data
- session history or logs depending on workflow

Operators should treat snapshot files as potentially sensitive because they may contain device topology, routing, or interface state.

## Deterministic Core

MindNet’s main trust boundary is its deterministic analysis path:

- collectors gather device outputs
- parsers normalize them into typed snapshot data
- the rule engine produces findings from that structured state

Any AI-assisted explanation layer should consume this evidence rather than replace it.

## Threat Model Assumptions

MindNet assumes:

- the operator is authorized to access the device
- device output may contain sensitive infrastructure details
- local workstations may be less controlled than server-side systems
- convenience features should not quietly expand data exposure

## Safe Defaults

- mock mode is available for safe testing
- outbound telemetry is disabled by default
- connector secrets are not intended to be stored in tracked project files
- analysis is read-only by design

## Reporting Security Issues

Avoid opening public issues with sensitive vulnerability details until the project has a dedicated private disclosure channel.
