"""Dataclasses for pueo-kb manifest entries, runbook frontmatter, and evidence files."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

VALID_STATES = {"seed", "candidate", "validated", "flagged"}

REQUIRED_FRONTMATTER_FIELDS = {"id", "type", "state"}


@dataclass
class RunbookFrontmatter:
    id: str
    type: str
    state: str
    signature: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    integrations: List[str] = field(default_factory=lambda: ["all"])
    ha_version_min: Optional[str] = None
    ha_version_max: Optional[str] = None
    contributed_at: Optional[str] = None

    def validate(self) -> List[str]:
        errors = []
        if not self.id:
            errors.append("id is required")
        if self.type != "runbook":
            errors.append(f"type must be 'runbook', got {self.type!r}")
        if self.state not in VALID_STATES:
            errors.append(f"state must be one of {VALID_STATES}, got {self.state!r}")
        return errors


@dataclass
class CommunityStats:
    successes: int = 0
    failures: int = 0
    instances: int = 0

    def validate(self) -> List[str]:
        errors = []
        for field_name in ("successes", "failures", "instances"):
            val = getattr(self, field_name)
            if not isinstance(val, int) or val < 0:
                errors.append(f"community_stats.{field_name} must be a non-negative int")
        return errors

    def to_dict(self) -> dict:
        return {
            "successes": self.successes,
            "failures": self.failures,
            "instances": self.instances,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "CommunityStats":
        return cls(
            successes=d.get("successes", 0),
            failures=d.get("failures", 0),
            instances=d.get("instances", 0),
        )


@dataclass
class ManifestEntry:
    id: str
    type: str
    path: str
    sha256: str
    state: str
    signature: Optional[str]
    tags: List[str]
    integrations: List[str]
    ha_version_min: Optional[str]
    ha_version_max: Optional[str]
    contributed_at: Optional[str]
    community_stats: CommunityStats

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "path": self.path,
            "sha256": self.sha256,
            "state": self.state,
            "signature": self.signature,
            "tags": self.tags,
            "integrations": self.integrations,
            "ha_version_min": self.ha_version_min,
            "ha_version_max": self.ha_version_max,
            "contributed_at": self.contributed_at,
            "community_stats": self.community_stats.to_dict(),
        }

    def validate(self) -> List[str]:
        errors = []
        if not self.id:
            errors.append("id is required")
        if self.state not in VALID_STATES:
            errors.append(f"state must be one of {VALID_STATES}, got {self.state!r}")
        if not self.sha256 or len(self.sha256) != 64:
            errors.append("sha256 must be a 64-character hex string")
        errors.extend(self.community_stats.validate())
        return errors


@dataclass
class EvidenceRunbookStats:
    sha256: str
    signature: str
    successes: int
    failures: int
    episodes: List[str] = field(default_factory=list)

    def validate(self) -> List[str]:
        errors = []
        if not self.sha256:
            errors.append("sha256 is required")
        if not self.signature:
            errors.append("signature is required")
        if not isinstance(self.successes, int) or self.successes < 0:
            errors.append("successes must be a non-negative int")
        if not isinstance(self.failures, int) or self.failures < 0:
            errors.append("failures must be a non-negative int")
        return errors

    @classmethod
    def from_dict(cls, d: dict) -> "EvidenceRunbookStats":
        return cls(
            sha256=d.get("sha256", ""),
            signature=d.get("signature", ""),
            successes=d.get("successes", 0),
            failures=d.get("failures", 0),
            episodes=d.get("episodes", []),
        )


@dataclass
class EvidenceFile:
    instance_id: str
    pueo_version: str
    updated_at: str
    runbooks: Dict[str, EvidenceRunbookStats]

    REQUIRED_FIELDS = {"instance_id", "pueo_version", "updated_at", "runbooks"}

    def validate(self) -> List[str]:
        errors = []
        if not self.instance_id:
            errors.append("instance_id is required")
        if not self.pueo_version:
            errors.append("pueo_version is required")
        if not self.updated_at:
            errors.append("updated_at is required")
        for kb_id, stats in self.runbooks.items():
            for err in stats.validate():
                errors.append(f"runbooks.{kb_id}: {err}")
        return errors

    @classmethod
    def from_dict(cls, d: dict) -> "EvidenceFile":
        runbooks = {
            kb_id: EvidenceRunbookStats.from_dict(rb)
            for kb_id, rb in d.get("runbooks", {}).items()
        }
        return cls(
            instance_id=d.get("instance_id", ""),
            pueo_version=d.get("pueo_version", ""),
            updated_at=d.get("updated_at", ""),
            runbooks=runbooks,
        )
