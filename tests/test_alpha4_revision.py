from __future__ import annotations

from pathlib import Path

from tools.alpha4_revision_paired_expression import check_paired_expression
from tools.validate_alpha4_revision import (
    parse_seed_binding,
    validate_causal,
    validate_core_surface,
    validate_seed_root,
    validate_subject,
)
from tools.validate_repository_minimal import main as validate_repository_minimal

ROOT = Path(__file__).resolve().parents[1]
SEED_ROOT = Path(__file__).resolve().parents[2] / "_seed/aset-seed-main"


def test_repository_is_minimal() -> None:
    assert validate_repository_minimal() == 0


def test_alpha4_subject_is_minimal() -> None:
    validate_subject()
    validate_core_surface()
    validate_causal()


def test_exact_current_seed_binding() -> None:
    binding = parse_seed_binding()
    binding_text = (ROOT / "upstream/ASET_SEED_ALPHA4_BINDING.aset").read_text(
        encoding="utf-8"
    )
    workflow = (ROOT / ".github/workflows/verify.yml").read_text(encoding="utf-8")

    assert "COMMIT " not in binding_text
    assert len(binding.sources) == 10
    assert set(binding.companions) == {"ENGLISH", "PYTHON"}

    assert binding.release_tag in workflow
    assert binding.release_archive.removeprefix("sha256:") in workflow
    assert binding.profile_archive.removeprefix("sha256:") in workflow

    if SEED_ROOT.is_dir():
        validate_seed_root(SEED_ROOT, binding.sources)


def test_relational_core_has_no_owned_variable_state() -> None:
    relation = (ROOT / "revision/alpha4/formal/RevisionRelations.tla").read_text(
        encoding="utf-8"
    )
    assert "VARIABLE" not in relation
    assert "StateType == SUBSET ProposalUniverse" in relation
    assert relation.count("ProposeRevision(s, t, p) ==") == 1


def test_proposal_projects_to_seed_observation_not_recognition() -> None:
    bridge = (ROOT / "revision/alpha4/formal/SeedProjection.tla").read_text(
        encoding="utf-8"
    )
    proof = (ROOT / "revision/alpha4/formal/SeedBoundaryProofs.tla").read_text(
        encoding="utf-8"
    )

    assert "Seed!ObserveUnknown" in bridge
    assert 'recognition |-> "UNKNOWN"' in bridge
    assert "~ProjectedSeedEffectPermitted(p)" in proof


def test_revision_seed_boundary_contract() -> None:
    subject = (ROOT / "revision/alpha4/REVISION.aset").read_text(encoding="utf-8")
    proof = (ROOT / "revision/alpha4/formal/SeedBoundaryProofs.tla").read_text(
        encoding="utf-8"
    )

    bindings = [
        line for line in subject.splitlines() if line.startswith("SEED-EXTENSION-BIND ")
    ]
    assert bindings == [
        "SEED-EXTENSION-BIND OPERATIONAL OBSERVE-UNKNOWN PROPOSE-REVISION",
        "SEED-EXTENSION-BIND RELATIONAL ObserveUnknown ProposeRevision",
        "SEED-EXTENSION-BIND CAUSAL OBSERVE-UNKNOWN PROPOSE-REVISION",
    ]
    assert "SEED-PROJECTION PROPOSE-REVISION OBSERVE-UNKNOWN" in subject
    assert "SEED-RECOGNITION-OWNER TARGET-LOCAL-SEED" in subject
    assert "EFFECT-PERMITTED-BY-REVISION NEVER" in subject
    assert "RevisionPreservesSeedBoundary" in proof


def test_paired_expression_exhaustive_bounded_surface() -> None:
    evidence = check_paired_expression()
    assert evidence["status"] == "PASS"
    assert evidence["valid_proposals"] == 12
    assert evidence["states_checked"] == 4096
    assert evidence["cases_checked"] == 147456


def test_public_and_machine_identity_is_aset_revision() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    subject = (ROOT / "revision/alpha4/REVISION.aset").read_text(encoding="utf-8")
    assert readme.startswith("# ASET Revision\n")
    assert 'title: "ASET Revision"' in citation
    assert (
        'repository-code: "https://github.com/attractor-set/aset-revision"' in citation
    )
    assert 'family-names: "Prychyna"' in citation
    assert 'given-names: "Dzmitry"' in citation
    assert "Copyright 2026 Dzmitry Prychyna" in notice
    assert "Attractor Set" in notice
    assert "ASET-REVISION-0.4-ALPHA" in subject
