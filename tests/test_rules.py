"""Tests for deterministic rule registry and evaluation."""

from netmind.explain import build_snapshot
from netmind.mock_device import MOCK_RESPONSES
from netmind.models import FindingSeverity
from netmind.rules import evaluate_snapshot, get_rule_registry


def _mock_snapshot():
    raw_outputs = {
        cmd: MOCK_RESPONSES[cmd]
        for cmd in MOCK_RESPONSES
        if not cmd.startswith("show interfaces gi")
    }
    return build_snapshot("10.0.0.1", "2024-01-01T00:00:00+00:00", raw_outputs)


def test_rule_registry_has_expected_rules():
    registry = get_rule_registry()
    names = [rule.__name__ for rule in registry]
    assert names == [
        "check_interfaces_down",
        "check_admin_down",
        "check_err_disabled",
        "check_interface_errors",
        "check_cdp_neighbors",
        "check_routing",
    ]


def test_evaluate_snapshot_returns_sorted_findings():
    findings = evaluate_snapshot(_mock_snapshot())
    assert findings

    severity_rank = {
        FindingSeverity.CRITICAL: 0,
        FindingSeverity.WARNING: 1,
        FindingSeverity.INFO: 2,
        FindingSeverity.OK: 3,
    }
    ranks = [severity_rank[finding.severity] for finding in findings]
    assert ranks == sorted(ranks)
