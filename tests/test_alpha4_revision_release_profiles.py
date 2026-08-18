from __future__ import annotations

import json
from pathlib import Path

from tools.alpha4_revision_expression_airgap_verifier import check_expression
from tools.alpha4_revision_python_sqlite_persistence_gate import check_persistence
from tools.alpha4_revision_release_profile_congruence import (
    check_release_profile_congruence,
)
from tools.alpha4_revision_release_profiles import build_release_profiles


def test_generated_release_companions_are_congruent(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    profiles = tmp_path / "profiles"
    generated = build_release_profiles(root, profiles)
    evidence = check_release_profile_congruence(profiles)
    assert evidence["status"] == "PASS"
    assert generated["record"]["state"] == "proposals"
    assert generated["record"]["transition"] == "PROPOSE-REVISION"
    assert generated["record"]["seed_projection"] == "OBSERVE-UNKNOWN"


def test_generated_python_is_independently_airgapped(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    profiles = tmp_path / "profiles"
    build_release_profiles(root, profiles)
    evidence = check_expression(profiles / "python/aset_revision_alpha4.py")
    assert evidence["status"] == "PASS"
    assert evidence["cases_checked"] == 147456
    assert evidence["valid_proposals"] == 12
    assert evidence["states_checked"] == 4096


def test_python_sqlite_is_persistence_only(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    profiles = tmp_path / "profiles"
    build_release_profiles(root, profiles)
    evidence = check_persistence(profiles)
    assert evidence["status"] == "PASS"
    assert evidence["semantic_delta"] == "NONE"
    assert evidence["semantic_precedence"] == "NONE"
    assert evidence["schema_semantic_fields"] == ["proposals"]
    assert evidence["base_expression_congruence_cases"] == 2880

    binding = json.loads(
        (profiles / "python-sqlite/PERSISTENCE_EXTENSION.json").read_text(
            encoding="utf-8"
        )
    )
    assert binding["relation"] == "PERSISTENCE_EXTENSION"
    assert binding["base_expression"]["profile"] == "python"
    assert binding["extension"]["profile"] == "python-sqlite"


def test_generated_release_companions_use_aset_revision_public_identity(
    tmp_path: Path,
) -> None:
    root = Path(__file__).resolve().parents[1]
    profiles = tmp_path / "profiles"
    build_release_profiles(root, profiles)
    assert (profiles / "en/Revision.md").is_file()
    assert (profiles / "python/aset_revision_alpha4.py").is_file()
    assert (profiles / "python-sqlite/aset_revision_alpha4_sqlite.py").is_file()


def test_release_admission_certificate_and_public_audit_bind_exact_bytes(
    tmp_path: Path,
) -> None:
    import hashlib
    import zipfile

    from tools.alpha4_revision_public_release_audit import check_public_release
    from tools.alpha4_revision_release_admission_certificate import (
        check_release_admission,
    )
    from tools.build_alpha4_revision_release import (
        build_profiles,
        build_source_release,
        tree_digest,
        zip_tree,
    )

    root = Path(__file__).resolve().parents[1]
    release = tmp_path / "ASET-Revision-0.4alpha"
    profiles = tmp_path / "ASET-Revision-0.4alpha-profiles"
    build_source_release(release)
    build_profiles(profiles, tree_digest(release))
    release_archive = tmp_path / "ASET-Revision-0.4alpha.zip"
    profiles_archive = tmp_path / "ASET-Revision-0.4alpha-profiles.zip"
    zip_tree(release, release_archive, "ASET-Revision-0.4alpha")
    zip_tree(profiles, profiles_archive, "ASET-Revision-0.4alpha-profiles")

    python_path = profiles / "python/aset_revision_alpha4.py"
    binding = json.loads(
        (profiles / "python-sqlite/PERSISTENCE_EXTENSION.json").read_text(
            encoding="utf-8"
        )
    )
    sqlite_path = profiles / binding["extension"]["path"]

    def digest(path: Path) -> str:
        return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()

    tlaps_path = tmp_path / "tlaps.json"
    proofs = [
        (
            "COMPONENT_COMPOSITION",
            "revision/alpha4/formal/ComponentCompositionProofs.tla",
            "RevisionProposalSafety",
            11,
        ),
        (
            "OPERATIONAL_RELATIONAL_PAIRING",
            "revision/alpha4/formal/OperationalRelationalPairingProofs.tla",
            "OperationalRelationalPairing",
            3,
        ),
        (
            "SEED_PROJECTION",
            "revision/alpha4/formal/SeedProjectionProofs.tla",
            "RevisionProposalPreservesSeedRecognitionBoundary",
            16,
        ),
    ]
    tlaps_path.write_text(
        json.dumps(
            {
                "document_type": "aset-revision-alpha4-tlaps-evidence",
                "project": "ASET Revision",
                "subject_id": "ASET-REVISION-0.4-ALPHA",
                "representation_id": "0.4alpha",
                "semantic_precedence": "NONE",
                "proofs": [
                    {
                        "id": proof_id,
                        "path": relative,
                        "sha256": digest(root / relative),
                        "final_theorem": theorem,
                        "obligations": count,
                        "status": "PASS",
                    }
                    for proof_id, relative, theorem, count in proofs
                ],
                "total_obligations": 30,
                "status": "PASS",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    expression_path = tmp_path / "expression.json"
    expression_path.write_text(
        json.dumps(
            {
                "document_type": "aset-revision-python-expression-airgap-evidence",
                "project": "ASET Revision",
                "expression": {
                    "path": python_path.name,
                    "sha256": digest(python_path),
                },
                "cases_checked": 147456,
                "valid_proposals": 12,
                "states_checked": 4096,
                "semantic_precedence": "NONE",
                "seed_projection": "OBSERVE-UNKNOWN",
                "status": "PASS",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    persistence_path = tmp_path / "persistence.json"
    persistence_path.write_text(
        json.dumps(
            {
                "document_type": "aset-revision-python-sqlite-persistence-evidence",
                "project": "ASET Revision",
                "relation": "PERSISTENCE_EXTENSION_OF_EXACT_PYTHON_EXPRESSION",
                "base_expression_congruence_cases": 2880,
                "rollback_checks": 2076,
                "restart_round_trip_checks": 12,
                "semantic_delta": "NONE",
                "semantic_precedence": "NONE",
                "schema_semantic_fields": ["proposals"],
                "base_expression_binding": {
                    "path": binding["base_expression"]["path"],
                    "sha256": digest(python_path),
                },
                "extension_binding": {
                    "path": binding["extension"]["path"],
                    "sha256": digest(sqlite_path),
                },
                "materialization_boundary": {
                    "profile_tree_unchanged": True,
                    "python_bytecode_written": False,
                },
                "profile_tree_unchanged": True,
                "status": "PASS",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    certificate = check_release_admission(
        tlaps_evidence_path=tlaps_path,
        expression_evidence_path=expression_path,
        persistence_evidence_path=persistence_path,
        release_root=release,
        profiles_root=profiles,
        release_archive=release_archive,
        profiles_archive=profiles_archive,
    )
    assert certificate["status"] == "PASS"
    assert certificate["project"] == "ASET Revision"
    assert certificate["assurance"]["tlaps_obligations"] == 30
    assert certificate["assurance"]["sqlite_semantic_delta"] == "NONE"

    certificate_path = tmp_path / "certificate.json"
    certificate_path.write_text(
        json.dumps(certificate, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    audit = check_public_release(
        release,
        profiles,
        release_archive,
        profiles_archive,
        certificate_path,
    )
    assert audit["status"] == "PASS"
    assert audit["repository_locator"] == "EXACT"
    with zipfile.ZipFile(release_archive) as archive:
        assert all(
            name.startswith("ASET-Revision-0.4alpha/") for name in archive.namelist()
        )
