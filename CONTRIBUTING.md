# Contributing

MindNet is early, but it is not a throwaway scripts repository. Contributions
should improve the project as infrastructure intelligence software, not only as
an ad hoc CLI utility.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .[dev]
```

For isolated manual CLI testing:

```bash
pipx install .
```

## Running the project locally

```bash
mindnet --help
mindnet version
```

Mock mode for repeatable local testing:

```bash
export NETMIND_MOCK=true
mindnet audit 10.0.0.1
mindnet analyze-file mock_data/show__ip__route.txt
```

## Running tests

```bash
export PYTHONPATH=src
python -m compileall src tests
pytest -q
```

If the local shell environment behaves differently from CI, document that in the
PR instead of claiming verification you did not complete.

## Contributing architecture improvements

Architecture contributions are welcome, but they should be incremental and
grounded in the current repository rather than speculative redesigns.

Good architecture contributions:
- clearer boundaries between context, reasoning, and execution
- improved snapshot/data models
- better connector abstractions
- clearer planning or intent interfaces
- more realistic documentation of future evolution

When making an architecture change:
- explain the problem first
- show why the new boundary is useful
- keep the current codebase runnable
- update `README.md`, `AGENT.md`, and architecture docs as needed

## Adding connectors or reasoning modules

For connectors:
- keep them behind explicit connector abstractions
- do not hardwire new collection logic into the CLI layer
- document authentication and trust assumptions

For reasoning modules:
- prefer deterministic behavior first
- keep evidence traceable
- separate parsing from evaluation where practical
- avoid introducing opaque AI-only behavior without a clear deterministic baseline

## Proposing changes safely

Please keep changes focused and explain tradeoffs clearly.

Before opening a PR:
- keep the scope narrow
- include tests where practical
- update docs for user-visible behavior
- call out any security or trust-boundary implications
- avoid mixing large docs rewrites with unrelated code changes unless they are tightly coupled

## Project guardrails

- keep MindNet local-first by default
- do not add hidden telemetry
- do not merge MindNet's identity with execution-oriented tools such as MidMan
- do not add hosted/SaaS assumptions without explicit discussion
- keep secrets out of the repository

## Coding standards

- Python 3.11+
- English-only code and code comments
- type hints on public functions
- small focused modules
- explicit error handling
