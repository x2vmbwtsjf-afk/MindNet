"""Persistence helpers for DeviceSnapshot JSON export/import."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .models import DeviceSnapshot, Interface, Neighbor, Route

SNAPSHOT_SCHEMA_VERSION = "1"


def snapshot_to_dict(snapshot: DeviceSnapshot) -> dict:
    """Serialize a DeviceSnapshot to a JSON-friendly dictionary."""
    payload = asdict(snapshot)
    payload["schema_version"] = SNAPSHOT_SCHEMA_VERSION
    return payload


def snapshot_from_dict(payload: dict) -> DeviceSnapshot:
    """Deserialize a DeviceSnapshot from a dictionary payload."""
    schema_version = str(payload.get("schema_version", SNAPSHOT_SCHEMA_VERSION))
    if schema_version != SNAPSHOT_SCHEMA_VERSION:
        raise ValueError(
            f"Unsupported snapshot schema version: {schema_version}. "
            f"Expected {SNAPSHOT_SCHEMA_VERSION}."
        )

    interfaces = [Interface(**item) for item in payload.get("interfaces", [])]
    routes = [Route(**item) for item in payload.get("routes", [])]
    neighbors = [Neighbor(**item) for item in payload.get("neighbors", [])]

    return DeviceSnapshot(
        host=payload["host"],
        timestamp=payload["timestamp"],
        interfaces=interfaces,
        routes=routes,
        neighbors=neighbors,
        raw_outputs=payload.get("raw_outputs", {}),
        schema_version=schema_version,
    )


def save_snapshot(snapshot: DeviceSnapshot, path: str | Path) -> Path:
    """Save a DeviceSnapshot as formatted JSON."""
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(snapshot_to_dict(snapshot), indent=2, sort_keys=True), encoding="utf-8")
    return target


def load_snapshot(path: str | Path) -> DeviceSnapshot:
    """Load a DeviceSnapshot from a JSON file."""
    source = Path(path).expanduser().resolve()
    payload = json.loads(source.read_text(encoding="utf-8"))
    return snapshot_from_dict(payload)
