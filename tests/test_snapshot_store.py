"""Tests for snapshot JSON persistence helpers."""

from pathlib import Path

from netmind.explain import build_snapshot
from netmind.mock_device import MOCK_RESPONSES
from netmind.snapshot_store import load_snapshot, save_snapshot, snapshot_from_dict, snapshot_to_dict
from netmind.rules import evaluate_snapshot


def _mock_snapshot():
    raw_outputs = {
        cmd: MOCK_RESPONSES[cmd]
        for cmd in MOCK_RESPONSES
        if not cmd.startswith("show interfaces gi")
    }
    return build_snapshot("10.0.0.1", "2024-01-01T00:00:00+00:00", raw_outputs)


def test_snapshot_to_dict_contains_schema():
    payload = snapshot_to_dict(_mock_snapshot())
    assert payload["schema_version"] == "1"
    assert payload["host"] == "10.0.0.1"


def test_snapshot_round_trip_dict():
    snapshot = _mock_snapshot()
    payload = snapshot_to_dict(snapshot)
    restored = snapshot_from_dict(payload)
    assert restored.host == snapshot.host
    assert len(restored.interfaces) == len(snapshot.interfaces)
    assert len(restored.routes) == len(snapshot.routes)
    assert len(restored.neighbors) == len(snapshot.neighbors)


def test_snapshot_save_and_load(tmp_path: Path):
    snapshot = _mock_snapshot()
    path = tmp_path / "snapshot.json"
    save_snapshot(snapshot, path)
    restored = load_snapshot(path)
    assert restored.host == "10.0.0.1"
    assert restored.schema_version == "1"


def test_loaded_snapshot_can_be_analyzed(tmp_path: Path):
    snapshot = _mock_snapshot()
    path = tmp_path / "snapshot.json"
    save_snapshot(snapshot, path)
    restored = load_snapshot(path)
    findings = evaluate_snapshot(restored)
    assert findings
