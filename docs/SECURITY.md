# Security Model

MindNet is an infrastructure intelligence project. That means its security model
must be stricter than a normal local utility.

This document defines the baseline security expectations for the project.

## Core principles

- local-first by default
- explicit execution boundaries
- no silent credential leakage
- deterministic behavior before autonomy
- secure-by-default integration posture

## Local-first expectations

MindNet should default to local execution and local storage unless a future
integration explicitly changes that behavior.

Implications:
- infrastructure context should not be sent off-box by default
- stored state should remain local unless exported intentionally
- diagnostics should be reproducible without a hosted dependency

## Credential handling

MindNet already uses a split model:
- non-sensitive connector metadata in local config
- secrets in the OS keyring

Security expectations:
- never store passwords or tokens in plaintext project files
- never print secrets in CLI output
- never log secrets in debug paths
- prefer OS-native secret storage over custom encryption

## Execution boundaries

MindNet is primarily a reasoning and analysis layer.

By default, it should:
- inspect
- model
- reason
- explain

It should not:
- make destructive changes automatically
- apply remediation without explicit operator intent
- hide execution side effects behind AI language

If MindNet later integrates with execution systems, those boundaries must remain
visible and auditable.

## Safe integration with external tools

Future integrations may include:
- SSH
- infrastructure APIs
- configuration systems
- execution tools such as MidMan

Integration rules:
- connectors should be explicit and typed
- trust boundaries should be documented
- execution handoff should be separable from reasoning
- external actions should require clear operator intent

## Threat assumptions

MindNet should assume:
- infrastructure data is sensitive
- topology and routing information may be confidential
- credentials are valuable targets
- AI-generated output can be wrong or overconfident
- logs and exported snapshots may leave the local environment if mishandled

## What MindNet should never do by default

MindNet should never, by default:
- exfiltrate infrastructure context to a remote service
- store plaintext credentials in repository files
- execute changes on infrastructure automatically
- claim certainty when reasoning is based on incomplete context
- collapse reasoning and execution into an opaque single step

## Contributor expectations

When contributing:
- preserve local-first behavior
- avoid adding hidden outbound dependencies
- document any new trust boundary
- keep secrets out of fixtures and examples
- update this document if a change affects the security model

## Reporting security concerns

Until a formal disclosure process exists:
- do not publish sensitive exploit details in public issues
- report serious concerns privately to the maintainer first
- include reproduction detail, scope, and impact clearly
