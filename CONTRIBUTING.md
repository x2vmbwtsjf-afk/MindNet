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

## Coding Standards

- Python 3.11+
- type hints on public functions
- English-only code and code comments
- small focused modules
- explicit error handling
