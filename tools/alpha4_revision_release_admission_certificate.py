#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "ASET Revision"
REPOSITORY = "https://github.com/attractor-set/aset-revision"
SUBJECT_ID = "ASET-REVISION-0.4-ALPHA"
REPRESENTATION_ID = "0.4alpha"


class ReleaseAdmissionError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReleaseAdmissionError(message)


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def load_json(path: Path, expected_type: str) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path.name}: document must be an object")
    require(
        value.get("document_type") == expected_type,
        f"{path.name}: unexpected document type",
    )
    require(value.get("status") == "PASS", f"{path.name}: evidence is not PASS")
    return value


def check_release_admission(
    *,
    tlaps_evidence_path: Path,
    expression_evidence_path: Path,
    persistence_evidence_path: Path,
    release_root: Path,
    profiles_root: Path,
    release_archive: Path,
    profiles_archive: Path,
) -> dict[str, Any]:
    tlaps = load_json(tlaps_evidence_path, "aset-revision-alpha4-tlaps-evidence")
    expression = load_json(
        expression_evidence_path,
        "aset-revision-python-expression-airgap-evidence",
    )
    persistence = load_json(
        persistence_evidence_path,
        "aset-revision-python-sqlite-persistence-evidence",
    )

    release_manifest_path = release_root / "RELEASE_MANIFEST.json"
    profile_manifest_path = profiles_root / "RELEASE_PROFILE_MANIFEST.json"
    require(release_manifest_path.is_file(), "source release manifest missing")
    require(profile_manifest_path.is_file(), "profile release manifest missing")
    release_manifest = json.loads(release_manifest_path.read_text(encoding="utf-8"))
    profile_manifest = json.loads(profile_manifest_path.read_text(encoding="utf-8"))

    require(
        release_manifest.get("document_type")
        == "aset-revision-release-materialization",
        "unexpected source release manifest type",
    )
    require(
        profile_manifest.get("document_type")
        == "aset-revision-ci-release-companion-materialization",
        "unexpected profile release manifest type",
    )
    for manifest in (release_manifest, profile_manifest):
        require(manifest.get("project") == PROJECT, "project identity mismatch")
        require(
            manifest.get("repository") == REPOSITORY,
            "repository identity mismatch",
        )
        require(
            manifest.get("representation_id") == REPRESENTATION_ID,
            "representation identity mismatch",
        )
        require(manifest.get("subject_id") == SUBJECT_ID, "semantic subject mismatch")
        require(
            manifest.get("semantic_precedence") == "NONE",
            "release acquired semantic precedence",
        )

    release_tree = tree_digest(release_root)
    profiles_tree = tree_digest(profiles_root)
    require(
        profile_manifest.get("source_release_tree_digest") == release_tree,
        "profiles are not bound to exact source release tree",
    )
    require(release_archive.is_file(), "source release archive missing")
    require(profiles_archive.is_file(), "profile release archive missing")
    require(
        sha256(release_root / "LICENSE") == sha256(ROOT / "LICENSE"),
        "release LICENSE differs from repository LICENSE",
    )
    require(
        sha256(release_root / "NOTICE") == sha256(ROOT / "NOTICE"),
        "release NOTICE differs from repository NOTICE",
    )

    require(tlaps.get("subject_id") == SUBJECT_ID, "TLAPS subject mismatch")
    require(tlaps.get("total_obligations") == 30, "TLAPS total must be 30")
    expected_counts = {
        "COMPONENT_COMPOSITION": 11,
        "OPERATIONAL_RELATIONAL_PAIRING": 3,
        "SEED_BOUNDARY": 16,
    }
    proof_records = tlaps.get("proofs")
    require(isinstance(proof_records, list), "TLAPS proof records missing")
    observed_counts = {
        str(item.get("id")): item.get("obligations")
        for item in proof_records
        if isinstance(item, dict)
    }
    require(observed_counts == expected_counts, "TLAPS proof-count identity mismatch")
    for item in proof_records:
        require(isinstance(item, dict), "invalid TLAPS proof record")
        relative = str(item.get("path", ""))
        proof_path = ROOT / relative
        require(proof_path.is_file(), f"TLAPS proof source missing: {relative}")
        require(item.get("sha256") == sha256(proof_path), "TLAPS proof bytes drift")

    require(
        expression.get("cases_checked") == 147456,
        "Python air-gap case count drift",
    )
    require(expression.get("semantic_precedence") == "NONE", "Python precedence drift")
    require(
        expression.get("seed_projection") == "OBSERVE-UNKNOWN",
        "Python Seed projection drift",
    )
    expression_binding = expression.get("expression")
    require(isinstance(expression_binding, dict), "Python expression binding missing")
    python_path = profiles_root / "python/aset_revision_alpha4.py"
    require(python_path.is_file(), "generated Python expression missing")
    require(
        expression_binding.get("sha256") == sha256(python_path),
        "Python air-gap used different bytes",
    )

    require(
        persistence.get("base_expression_congruence_cases") == 2880,
        "SQLite congruence case count drift",
    )
    require(persistence.get("rollback_checks") == 2076, "SQLite rollback count drift")
    require(
        persistence.get("restart_round_trip_checks") == 12,
        "SQLite restart count drift",
    )
    require(persistence.get("semantic_delta") == "NONE", "SQLite semantic delta drift")
    require(persistence.get("semantic_precedence") == "NONE", "SQLite precedence drift")
    base_binding = persistence.get("base_expression_binding")
    extension_binding = persistence.get("extension_binding")
    require(isinstance(base_binding, dict), "SQLite base binding missing")
    require(isinstance(extension_binding, dict), "SQLite extension binding missing")
    require(
        base_binding.get("sha256") == sha256(python_path),
        "SQLite base differs from admitted Python",
    )
    sqlite_path = profiles_root / "python-sqlite/aset_revision_alpha4_sqlite.py"
    require(sqlite_path.is_file(), "SQLite extension missing")
    require(
        extension_binding.get("sha256") == sha256(sqlite_path),
        "SQLite extension bytes drift",
    )
    boundary = persistence.get("materialization_boundary")
    require(isinstance(boundary, dict), "SQLite materialization boundary missing")
    require(
        boundary.get("profile_tree_unchanged") is True,
        "SQLite gate mutated profile tree",
    )
    require(
        boundary.get("python_bytecode_written") is False,
        "SQLite gate wrote bytecode",
    )

    notice = ROOT / "NOTICE"
    citation = ROOT / "CITATION.cff"
    license_path = ROOT / "LICENSE"
    require(
        "Copyright 2026 Dzmitry Prychyna" in notice.read_text(encoding="utf-8"),
        "copyright holder missing",
    )
    require(
        "Attractor Set" in notice.read_text(encoding="utf-8"),
        "public author identity missing",
    )
    citation_text = citation.read_text(encoding="utf-8")
    require(
        'title: "ASET Revision"' in citation_text, "citation project identity mismatch"
    )
    require(
        f'repository-code: "{REPOSITORY}"' in citation_text,
        "citation repository mismatch",
    )
    require(
        "Apache License" in license_path.read_text(encoding="utf-8"),
        "Apache-2.0 license missing",
    )

    return {
        "document_type": "aset-revision-release-admission-certificate",
        "project": PROJECT,
        "repository": REPOSITORY,
        "representation_id": REPRESENTATION_ID,
        "subject_id": SUBJECT_ID,
        "semantic_precedence": "NONE",
        "release": {
            "tree_digest": release_tree,
            "archive_sha256": sha256(release_archive),
        },
        "profiles": {
            "tree_digest": profiles_tree,
            "archive_sha256": sha256(profiles_archive),
            "semantic_precedence": "NONE",
        },
        "assurance": {
            "tlaps_obligations": 30,
            "python_airgap_cases": 147456,
            "sqlite_congruence_cases": 2880,
            "sqlite_rollback_checks": 2076,
            "sqlite_restart_checks": 12,
            "sqlite_semantic_delta": "NONE",
        },
        "attribution": {
            "license": "Apache-2.0",
            "license_sha256": sha256(license_path),
            "notice_sha256": sha256(notice),
            "citation_sha256": sha256(citation),
        },
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tlaps-evidence", type=Path, required=True)
    parser.add_argument("--expression-evidence", type=Path, required=True)
    parser.add_argument("--persistence-evidence", type=Path, required=True)
    parser.add_argument("--release-root", type=Path, required=True)
    parser.add_argument("--profiles-root", type=Path, required=True)
    parser.add_argument("--release-archive", type=Path, required=True)
    parser.add_argument("--profiles-archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    certificate = check_release_admission(
        tlaps_evidence_path=args.tlaps_evidence.resolve(),
        expression_evidence_path=args.expression_evidence.resolve(),
        persistence_evidence_path=args.persistence_evidence.resolve(),
        release_root=args.release_root.resolve(),
        profiles_root=args.profiles_root.resolve(),
        release_archive=args.release_archive.resolve(),
        profiles_archive=args.profiles_archive.resolve(),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("ALPHA4_REVISION_RELEASE_ADMISSION_TLAPS=30/30 PASS")
    print("ALPHA4_REVISION_RELEASE_ADMISSION_PYTHON_AIRGAP=147456/147456 PASS")
    print("ALPHA4_REVISION_RELEASE_ADMISSION_SQLITE=2880/2880 PASS")
    print("ALPHA4_REVISION_RELEASE_ADMISSION_CERTIFICATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
