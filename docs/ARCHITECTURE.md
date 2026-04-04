# MindNet Architecture

MindNet is designed as a local-first infrastructure intelligence layer. The
current implementation is intentionally modest, but the architecture should be
understood as a foundation for a reasoning-oriented system rather than only a
CLI wrapper around SSH.

## Design intent

MindNet should evolve toward a system that can:
- ingest infrastructure context from multiple sources
- build structured models of state and relationships
- interpret operator intent
- plan actions before execution
- hand execution off to purpose-built systems

The project therefore separates:
- context collection
- modeling
- reasoning
- explanation
- execution handoff

## Current architecture

Today, the repository is centered on these working layers:

- `src/netmind/cli.py`
  - user-facing command surface
- `src/netmind/connectors/`
  - transport and connector abstraction
- `src/netmind/security/`
  - local config and credential handling
- `src/netmind/models.py`
  - typed infrastructure state objects
- `src/netmind/explain.py`
  - parsing and deterministic command understanding
- `src/netmind/rules.py`
  - deterministic findings and evaluation
- `src/netmind/snapshot_store.py`
  - persistence for structured state snapshots

## Architecture diagram

```text
                +----------------------+
                |      CLI / API       |
                |  commands, sessions  |
                +----------+-----------+
                           |
                           v
                +----------------------+
                |   Context Ingestion  |
                | SSH, file, stdin,    |
                | future API sources   |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Infrastructure Model |
                | interfaces, routes,  |
                | neighbors, snapshots |
                +----------+-----------+
                           |
                           v
                +----------------------+
                | Reasoning / Rules    |
                | findings, planning,  |
                | intent alignment     |
                +----------+-----------+
                           |
             +-------------+-------------+
             |                           |
             v                           v
  +----------------------+   +------------------------+
  | Explanation Layer    |   | Execution Handoff      |
  | summaries, guidance, |   | MidMan, scripts,       |
  | next-step narratives |   | orchestrators, future  |
  +----------------------+   +------------------------+
```

## Context ingestion

MindNet needs to accept context from more than one source.

Current sources:
- SSH command collection
- local file analysis
- stdin analysis
- mock data

Future sources:
- infrastructure APIs
- configuration repositories
- service inventory systems
- event streams

This layer should stay connector-oriented so the reasoning system does not care
whether state came from SSH, an API, or a saved bundle.

## Infrastructure modeling

The snapshot model is one of the most important architectural choices in the
current repository.

Instead of keeping analysis tied directly to raw command output, MindNet turns
inputs into typed structures such as:
- `Interface`
- `Route`
- `Neighbor`
- `Finding`
- `DeviceSnapshot`

This is what makes later reasoning possible. The system cannot plan or compare
state well if everything stays as raw text blobs.

## Intent parsing

Intent parsing is not implemented yet, but the architecture should clearly make
space for it.

Examples of operator intent:
- "Why is traffic leaving through the wrong path?"
- "What changed between yesterday and now?"
- "What is the safest next step?"
- "Plan, but do not execute, a remediation path."

Intent parsing belongs above raw parsing and above transport. It should consume:
- operator request
- current context
- prior session state
- available tools/connectors

and produce:
- analysis goal
- required context
- recommended plan

## Reasoning and planning layer

Right now, reasoning is deterministic and rule-driven. That is the correct
foundation.

Longer term, this layer should grow into:
- context correlation
- topology-aware reasoning
- plan generation
- explicit assumptions and confidence
- optional AI augmentation on top of structured evidence

The key constraint is that reasoning should remain inspectable. MindNet should
not become a black box that emits actions without traceable evidence.

## Tool and connector abstraction

MindNet already includes a connector abstraction. That matters because the
reasoning system should not be tightly coupled to SSH.

Connector abstraction supports:
- multiple collection methods
- safer testing and mock workflows
- future integration with APIs
- a clean execution handoff boundary

## Execution handoff

MindNet should not automatically become the execution layer for infrastructure.

Instead, it should be able to:
- produce structured findings
- recommend next steps
- generate explicit plans
- hand those plans to an execution-oriented tool such as MidMan

That boundary is important:
- MindNet should understand context and plan
- MidMan should execute safely

## Memory and state

The current repository already hints at local state handling through snapshots
and connector metadata. A more complete future memory model could include:
- saved investigations
- local session context
- prior findings
- topology views
- operator notes and assumptions

This memory should remain local-first by default.

## Local-first operation

Local-first is not a cosmetic property. It is a design constraint.

Why it matters:
- infrastructure data is sensitive
- operator trust depends on inspectability
- local workflows are easier to secure and debug
- deterministic reasoning is easier to validate locally

MindNet can later integrate outward, but its baseline operating mode should not
depend on a hosted control plane.

## Future multi-agent or orchestration possibilities

If MindNet evolves into a larger AI system, a useful decomposition might be:
- context agent
- reasoning agent
- planning agent
- execution handoff agent
- memory/session agent

That does not need to be implemented now. The important point is that the
current architecture should not block that path.

## Suggested future logical structure

Without forcing a codebase rewrite today, a future logical decomposition could
look like:

```text
src/netmind/
    core/
    context/
    reasoning/
    connectors/
    memory/
    orchestration/
```

The repository is not there yet, and it should not pretend to be there. But the
project should be documented with that direction in mind.
