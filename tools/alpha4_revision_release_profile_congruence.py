from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from tools.alpha4_revision_release_profiles import companion_record

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def parse_controlled_english(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    require(
        "Membership: external companion" in text,
        "English companion boundary missing",
    )
    require(
        "Semantic precedence: none" in text,
        "English semantic precedence boundary missing",
    )
    fields: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^([A-Za-z]+): `(.*)`$", line.strip())
        if match:
            fields[match.group(1)] = match.group(2)
    return {
        "component_id": "ASET-REVISION-COMPONENT-PROPOSE-REVISION",
        "operational_word": fields["Operational"],
        "formal_operator": fields["Relational"],
        "state": fields["State"],
        "transition": fields["Transition"],
        "validity": fields["Validity"],
        "freshness": fields["Freshness"],
        "effect": fields["Effect"],
        "seed_projection": fields["SeedProjection"],
        "terminal_recognition_owned": fields["TerminalRecognitionOwned"] == "TRUE",
        "effect_permission_owned": fields["EffectPermissionOwned"] == "TRUE",
    }


def check_english(profiles_root: Path) -> dict[str, Any]:
    expected = companion_record().copy()
    expected.pop("pairing_proof")
    actual = parse_controlled_english(profiles_root / "en/Revision.md")
    require(actual == expected, "controlled English differs from exact source record")
    return {
        "relation": "CONTROLLED_ROUND_TRIP_CONGRUENCE",
        "components_checked": 1,
        "status": "PASS",
    }


def check_python_binding(profiles_root: Path) -> dict[str, Any]:
    source = (profiles_root / "python/aset_revision_alpha4.py").read_text(
        encoding="utf-8"
    )
    for required in (
        'SEMANTIC_PRECEDENCE = "NONE"',
        'SEED_PROJECTION = "OBSERVE-UNKNOWN"',
        "TERMINAL_RECOGNITION_OWNED = False",
        "EFFECT_PERMISSION_OWNED = False",
        "def propose_revision(",
    ):
        require(required in source, f"generated Python boundary missing: {required}")
    return {
        "relation": "GENERATED_EXPRESSION_BOUNDARY",
        "semantic_precedence": "NONE",
        "status": "PASS",
    }


def check_sqlite_binding(profiles_root: Path) -> dict[str, Any]:
    path = profiles_root / "python-sqlite/PERSISTENCE_EXTENSION.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    require(value.get("relation") == "PERSISTENCE_EXTENSION", "SQLite relation drift")
    require(value.get("semantic_delta") == "NONE", "SQLite semantic delta must be NONE")
    require(
        value.get("semantic_precedence") == "NONE",
        "SQLite semantic precedence must be NONE",
    )
    base = value.get("base_expression")
    extension = value.get("extension")
    require(
        isinstance(base, dict) and isinstance(extension, dict),
        "SQLite binding incomplete",
    )
    base_path = profiles_root / str(base["path"])
    extension_path = profiles_root / str(extension["path"])
    require(
        base.get("sha256") == sha256(base_path),
        "SQLite base Python byte binding drift",
    )
    require(
        extension.get("sha256") == sha256(extension_path),
        "SQLite extension byte binding drift",
    )
    return {
        "relation": "PERSISTENCE_EXTENSION_OF_EXACT_PYTHON_EXPRESSION",
        "semantic_delta": "NONE",
        "semantic_precedence": "NONE",
        "status": "PASS",
    }


def check_release_profile_congruence(profiles_root: Path) -> dict[str, Any]:
    return {
        "document_type": "aset-revision-release-profile-congruence-evidence",
        "project": "ASET Revision",
        "profile_scope": "CI_RELEASE_COMPANIONS",
        "semantic_precedence": "NONE",
        "english": check_english(profiles_root),
        "python": check_python_binding(profiles_root),
        "python_sqlite": check_sqlite_binding(profiles_root),
        "status": "PASS",
    }
