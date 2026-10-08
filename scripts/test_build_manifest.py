"""Tests for build_manifest.py and schemas.py."""
from __future__ import annotations

import hashlib
import json
import textwrap
from pathlib import Path

import pytest

from build_manifest import build_manifest, compute_state, load_evidence, load_frontmatter
from schemas import CommunityStats, EvidenceFile, ManifestEntry, RunbookFrontmatter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_runbook(tmp_path: Path, name: str, frontmatter: str, body: str = "") -> Path:
    rb = tmp_path / "runbooks" / name
    rb.parent.mkdir(parents=True, exist_ok=True)
    rb.write_text(f"---\n{frontmatter}---\n\n{body}")
    return rb


def make_evidence(tmp_path: Path, instance_id: str, runbooks: dict) -> Path:
    ev_dir = tmp_path / "evidence"
    ev_dir.mkdir(exist_ok=True)
    ev = {
        "instance_id": instance_id,
        "pueo_version": "1.0.0",
        "updated_at": "2026-10-08T00:00:00Z",
        "runbooks": runbooks,
    }
    path = ev_dir / f"{instance_id}.json"
    path.write_text(json.dumps(ev))
    return path


# ---------------------------------------------------------------------------
# load_frontmatter
# ---------------------------------------------------------------------------

def test_load_frontmatter_basic(tmp_path):
    f = tmp_path / "rb.md"
    f.write_text("---\nid: test\ntype: runbook\nstate: seed\n---\n\nbody")
    fm = load_frontmatter(f)
    assert fm == {"id": "test", "type": "runbook", "state": "seed"}


def test_load_frontmatter_missing_returns_none(tmp_path):
    f = tmp_path / "rb.md"
    f.write_text("# Title\n\nNo frontmatter here.")
    assert load_frontmatter(f) is None


def test_load_frontmatter_unclosed_returns_none(tmp_path):
    f = tmp_path / "rb.md"
    f.write_text("---\nid: test\n")
    assert load_frontmatter(f) is None


# ---------------------------------------------------------------------------
# compute_state
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fm_state, cs, expected",
    [
        ("seed", {"successes": 10, "failures": 0, "instances": 5}, "seed"),
        ("candidate", {"successes": 0, "failures": 0, "instances": 0}, "candidate"),
        ("candidate", {"successes": 3, "failures": 0, "instances": 2}, "validated"),
        ("candidate", {"successes": 3, "failures": 0, "instances": 1}, "candidate"),
        ("candidate", {"successes": 2, "failures": 0, "instances": 2}, "candidate"),
        ("candidate", {"successes": 5, "failures": 1, "instances": 3}, "flagged"),
        ("validated", {"successes": 0, "failures": 1, "instances": 0}, "flagged"),
    ],
)
def test_compute_state(fm_state, cs, expected):
    assert compute_state(fm_state, cs) == expected


# ---------------------------------------------------------------------------
# load_evidence
# ---------------------------------------------------------------------------

def test_load_evidence_empty_dir(tmp_path):
    ev_dir = tmp_path / "evidence"
    ev_dir.mkdir()
    assert load_evidence(ev_dir) == {}


def test_load_evidence_missing_dir(tmp_path):
    assert load_evidence(tmp_path / "evidence") == {}


def test_load_evidence_aggregates_two_instances(tmp_path):
    make_evidence(
        tmp_path, "inst-a",
        {"rb_abc123": {"sha256": "x" * 64, "signature": "sig", "successes": 2, "failures": 0}}
    )
    make_evidence(
        tmp_path, "inst-b",
        {"rb_abc123": {"sha256": "x" * 64, "signature": "sig", "successes": 1, "failures": 0}}
    )
    stats = load_evidence(tmp_path / "evidence")
    assert stats["rb_abc123"]["successes"] == 3
    assert stats["rb_abc123"]["failures"] == 0
    assert stats["rb_abc123"]["instances"] == 2


def test_load_evidence_failure_counts(tmp_path):
    make_evidence(
        tmp_path, "inst-a",
        {"rb_xyz": {"sha256": "a" * 64, "signature": "sig", "successes": 1, "failures": 2}}
    )
    stats = load_evidence(tmp_path / "evidence")
    assert stats["rb_xyz"]["failures"] == 2
    assert stats["rb_xyz"]["instances"] == 1


def test_load_evidence_instance_counted_once_for_multiple_successes(tmp_path):
    make_evidence(
        tmp_path, "inst-a",
        {"rb_aaa": {"sha256": "b" * 64, "signature": "sig", "successes": 5, "failures": 0}}
    )
    stats = load_evidence(tmp_path / "evidence")
    assert stats["rb_aaa"]["instances"] == 1


def test_load_evidence_skips_malformed_file(tmp_path, capsys):
    ev_dir = tmp_path / "evidence"
    ev_dir.mkdir()
    (ev_dir / "bad.json").write_text("not json{{")
    stats = load_evidence(ev_dir)
    assert stats == {}
    _, err = capsys.readouterr()
    assert "WARN" in err


# ---------------------------------------------------------------------------
# build_manifest
# ---------------------------------------------------------------------------

def test_build_manifest_single_seed(tmp_path):
    make_runbook(
        tmp_path, "seed_test.md",
        "id: seed_test\ntype: runbook\nstate: seed\ntags: [test]\n"
        "integrations: [all]\nha_version_min: null\ncontributed_at: '2026-09-15'\n",
        "# Title\nBody text.",
    )
    entries, warnings = build_manifest(tmp_path)
    assert len(entries) == 1
    e = entries[0]
    assert e["id"] == "seed_test"
    assert e["state"] == "seed"
    assert e["community_stats"] == {"successes": 0, "failures": 0, "instances": 0}
    assert len(e["sha256"]) == 64
    assert not warnings


def test_build_manifest_skips_no_frontmatter(tmp_path, capsys):
    make_runbook(tmp_path, "valid.md",
                 "id: valid\ntype: runbook\nstate: seed\n", "body")
    no_fm = tmp_path / "runbooks" / "no_fm.md"
    no_fm.write_text("# No frontmatter\nJust text.")
    entries, warnings = build_manifest(tmp_path)
    assert len(entries) == 1
    assert any("no_fm.md" in w for w in warnings)


def test_build_manifest_candidate_promoted(tmp_path):
    make_runbook(
        tmp_path, "rb_abc.md",
        "id: rb_abc\ntype: runbook\nstate: candidate\n"
        "signature: 'some sig'\ntags: []\nintegrations: [all]\n",
        "body",
    )
    make_evidence(
        tmp_path, "inst-a",
        {"rb_abc": {"sha256": "x" * 64, "signature": "some sig", "successes": 2, "failures": 0}}
    )
    make_evidence(
        tmp_path, "inst-b",
        {"rb_abc": {"sha256": "x" * 64, "signature": "some sig", "successes": 1, "failures": 0}}
    )
    entries, _ = build_manifest(tmp_path)
    assert entries[0]["state"] == "validated"
    assert entries[0]["community_stats"]["instances"] == 2


def test_build_manifest_candidate_flagged_on_failure(tmp_path):
    make_runbook(
        tmp_path, "rb_def.md",
        "id: rb_def\ntype: runbook\nstate: candidate\nsignature: 'sig'\n",
        "body",
    )
    make_evidence(
        tmp_path, "inst-a",
        {"rb_def": {"sha256": "y" * 64, "signature": "sig", "successes": 5, "failures": 1}}
    )
    entries, _ = build_manifest(tmp_path)
    assert entries[0]["state"] == "flagged"


def test_build_manifest_sha256_matches_file(tmp_path):
    rb = make_runbook(
        tmp_path, "seed_x.md",
        "id: seed_x\ntype: runbook\nstate: seed\n", "content"
    )
    entries, _ = build_manifest(tmp_path)
    expected = hashlib.sha256(rb.read_bytes()).hexdigest()
    assert entries[0]["sha256"] == expected


def test_build_manifest_sorted_by_id(tmp_path):
    for name, rb_id in [("z_rb.md", "z_rb"), ("a_rb.md", "a_rb"), ("m_rb.md", "m_rb")]:
        make_runbook(tmp_path, name, f"id: {rb_id}\ntype: runbook\nstate: seed\n", "body")
    entries, _ = build_manifest(tmp_path)
    ids = [e["id"] for e in entries]
    assert ids == sorted(ids)


def test_build_manifest_no_runbooks_dir(tmp_path):
    with pytest.raises(FileNotFoundError):
        build_manifest(tmp_path)


# ---------------------------------------------------------------------------
# Schemas — RunbookFrontmatter
# ---------------------------------------------------------------------------

def test_runbook_frontmatter_valid():
    fm = RunbookFrontmatter(id="x", type="runbook", state="seed")
    assert fm.validate() == []


def test_runbook_frontmatter_invalid_state():
    fm = RunbookFrontmatter(id="x", type="runbook", state="unknown")
    assert any("state" in e for e in fm.validate())


def test_runbook_frontmatter_invalid_type():
    fm = RunbookFrontmatter(id="x", type="gap", state="seed")
    assert any("type" in e for e in fm.validate())


# ---------------------------------------------------------------------------
# Schemas — CommunityStats
# ---------------------------------------------------------------------------

def test_community_stats_valid():
    cs = CommunityStats(successes=3, failures=0, instances=2)
    assert cs.validate() == []
    assert cs.to_dict() == {"successes": 3, "failures": 0, "instances": 2}


def test_community_stats_negative_raises():
    cs = CommunityStats(successes=-1, failures=0, instances=0)
    assert cs.validate() != []


def test_community_stats_roundtrip():
    d = {"successes": 5, "failures": 1, "instances": 3}
    cs = CommunityStats.from_dict(d)
    assert cs.to_dict() == d


# ---------------------------------------------------------------------------
# Schemas — EvidenceFile
# ---------------------------------------------------------------------------

def test_evidence_file_valid():
    ev = EvidenceFile(
        instance_id="abc",
        pueo_version="1.0",
        updated_at="2026-10-08",
        runbooks={},
    )
    assert ev.validate() == []


def test_evidence_file_missing_instance_id():
    ev = EvidenceFile(instance_id="", pueo_version="1.0", updated_at="2026-10-08", runbooks={})
    assert any("instance_id" in e for e in ev.validate())


def test_evidence_file_roundtrip():
    d = {
        "instance_id": "test-instance",
        "pueo_version": "2.0",
        "updated_at": "2026-10-08T00:00:00Z",
        "runbooks": {
            "rb_abc123": {
                "sha256": "a" * 64,
                "signature": "sig text",
                "successes": 3,
                "failures": 0,
                "episodes": ["ep1", "ep2"],
            }
        },
    }
    ev = EvidenceFile.from_dict(d)
    assert ev.instance_id == "test-instance"
    assert ev.runbooks["rb_abc123"].successes == 3
    assert ev.runbooks["rb_abc123"].episodes == ["ep1", "ep2"]
