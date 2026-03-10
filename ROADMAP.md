# MindNet Roadmap

This roadmap is organized into six execution phases.

## Phase 1 — CLI MVP
Goal:
- Deliver a reliable local CLI foundation for day-to-day network troubleshooting.

Scope:
- Commands: `version`, `connect`, `run`, `audit`, `shell`
- SSH workflow abstraction with mock-mode fallback
- Structured findings + plain-language guidance + next commands
- Stable terminal UX and error handling

Exit Criteria:
- Fresh install to first successful mock audit in under 10 minutes
- Core commands validated in mock mode
- Basic parser and formatter regression tests passing

## Phase 2 — Snapshot Model
Goal:
- Represent network state as structured snapshots instead of ad-hoc command output.

Scope:
- Snapshot schema for interfaces, routes, neighbors, device metadata
- Local snapshot save/load format
- Snapshot versioning strategy for future compatibility

Exit Criteria:
- CLI can export and load snapshots locally
- Snapshot schema documented and test-covered
- Deterministic snapshot generation in mock and live paths

## Phase 3 — Rule Engine
Goal:
- Add deterministic analysis over snapshots with clear, testable rules.

Scope:
- Rule registry and evaluation pipeline
- Severity model and standardized evidence output
- Rule packs for interface, routing, and neighbor health

Exit Criteria:
- Rules run on snapshots without live device dependency
- Findings include severity, evidence, explanation seed, and recommended next checks
- Unit tests cover rule correctness and edge cases

## Phase 4 — Fabric Collection
Goal:
- Collect state across multiple devices/fabric nodes in one workflow.

Scope:
- Multi-device inventory input
- Collection orchestration (safe parallelism where appropriate)
- Aggregated snapshot for fabric-level reasoning

Exit Criteria:
- Multi-node collection completes with partial-failure tolerance
- Fabric snapshot contains per-device and normalized cross-device sections
- Collection logs are operator-readable and debuggable

## Phase 5 — Simulation
Goal:
- Evaluate potential failure scenarios against collected/snapshotted state.

Scope:
- Scenario model (link down, node down, control-plane loss)
- Impact estimation framework
- CLI simulation commands with explicit assumptions

Exit Criteria:
- Simulations produce reproducible impact summaries
- Output distinguishes facts from assumptions
- Baseline scenarios validated against mock lab topologies

## Phase 6 — AI Explanation
Goal:
- Add AI-assisted explanation and guided troubleshooting on top of deterministic outputs.

Scope:
- Optional AI layer (local-first preference)
- Prompting based on structured findings/snapshots/rule output
- Guided next-step narratives with confidence indicators

Exit Criteria:
- AI mode can be toggled without changing deterministic core behavior
- Explanations reference concrete evidence
- Safe fallback to non-AI output when unavailable

## Cross-Phase Guardrails
- Local-first, terminal-first architecture remains mandatory
- Deterministic analysis is always the source of truth
- No autonomous remediation by default
- Every phase must include tests and docs updates

---
Principle: keep MindNet practical, trustworthy, and operator-first at every stage.
