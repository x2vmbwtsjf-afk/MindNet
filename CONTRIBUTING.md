# Contributing

## Development Setup

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

## Local Checks

```bash
export PYTHONPATH=src
python -m compileall src tests
pytest -q
```

Use mock mode for repeatable local testing:

```bash
export NETMIND_MOCK=true
mindnet audit 10.0.0.1
```

## Running The CLI

```bash
mindnet --help
mindnet version
mindnet connect 10.0.0.1
mindnet audit 10.0.0.1
mindnet analyze-file mock_data/show__ip__route.txt
```

## Contribution Rules

- Keep the project local-first.
- Do not add web or SaaS assumptions.
- Prefer deterministic parsing and rules before AI features.
- Keep user-facing secrets out of source-controlled files.
- Update `README.md` when behavior changes.
- Update `AGENT.md` when architecture or agent workflow expectations change.

## Pull Requests

Before opening a PR:
- run tests locally
- keep the change focused
- add or update tests for behavioral changes
- document user-visible changes

## Extending Analysis Rules

Deterministic findings are part of the product’s core value, so rule changes should be deliberate.

When adding or changing rules:

1. update the relevant parsing or model layer only if the new signal truly belongs there
2. implement the rule in `src/netmind/rules.py`
3. add tests that cover both positive and negative cases
4. keep explanation text practical and evidence-based
5. avoid introducing AI-only behavior into the rule path

## Adding Connectors

Connector code lives under `src/netmind/connectors/`.

When adding a connector:

1. define a narrow connector capability
2. keep collection behavior explicit and easy to test
3. make secret handling compatible with `src/netmind/security/`
4. update the CLI docs if the operator workflow changes

## Snapshot And Parser Changes

If you change snapshot structure or command parsing:

- update tests in `tests/`
- keep backward compatibility in mind for saved snapshots where practical
- document the new fields or behavior in `README.md` or architecture docs

## Coding Standards

- Python 3.11+
- type hints on public functions
- English-only code and code comments
- small focused modules
- explicit error handling
