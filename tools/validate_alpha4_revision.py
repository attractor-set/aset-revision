from __future__ import annotations

import argparse
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/alpha4"
SUBJECT = BASE / "REVISION.aset"
FORTH = BASE / "operational/components.forth"
REL = BASE / "formal/RevisionRelations.tla"
OP = BASE / "formal/RestrictedOperationalSemantics.tla"
PAIR = BASE / "formal/OperationalRelationalPairingProofs.tla"
COMPOSE = BASE / "formal/ComponentCompositionProofs.tla"
SEED_PROJECTION = BASE / "formal/SeedProjection.tla"
SEED_PROOF = BASE / "formal/SeedProjectionProofs.tla"
CAUSAL = BASE / "causal/components.petri"
BINDING = ROOT / "upstream/ASET_SEED_ALPHA4_BINDING.aset"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def nonempty(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


@dataclass(frozen=True)
class SeedBinding:
    release_tag: str
    release_tree: str
    release_archive: str
    profile_tree: str
    profile_archive: str
    companions: dict[str, tuple[str, str]]
    sources: dict[str, str]


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


def parse_seed_binding(path: Path = BINDING) -> SeedBinding:
    lines = nonempty(path)
    require(
        lines[0] == "ASET-SEED-BINDING 1 ASET-SEED-0.4-ALPHA CONTENT-ADDRESSED",
        "Seed binding header mismatch",
    )
    require(
        "REPOSITORY https://github.com/attractor-set/aset-seed" in lines,
        "Seed repository locator mismatch",
    )
    require("COMPATIBILITY 0.3 NONE" in lines, "Seed compatibility boundary mismatch")
    require(
        "SEMANTIC-PRECEDENCE NONE" in lines,
        "Seed binding acquired semantic precedence",
    )
    require(
        "REQUIRED-SEED-PAIR ASET-COMPONENT-OBSERVE-UNKNOWN "
        "OBSERVE-UNKNOWN ObserveUnknown ObserveUnknownPairing" in lines,
        "required Seed OBSERVE-UNKNOWN pair missing",
    )
    require(
        "REVISION-PROJECTION PROPOSE-REVISION OBSERVE-UNKNOWN" in lines,
        "Revision Seed projection declaration mismatch",
    )
    require(
        all(not line.startswith("COMMIT ") for line in lines),
        "Git commit authority must remain outside content-addressed binding",
    )

    scalars: dict[str, str] = {}
    sources: dict[str, str] = {}
    companions: dict[str, tuple[str, str]] = {}

    for line in lines[1:]:
        tokens = line.split()
        key = tokens[0]

        if key in {
            "RELEASE-TAG",
            "RELEASE-TREE",
            "RELEASE-ARCHIVE",
            "PROFILE-TREE",
            "PROFILE-ARCHIVE",
        }:
            require(len(tokens) == 2, f"invalid Seed binding scalar: {line}")
            require(key not in scalars, f"duplicate Seed binding scalar: {key}")
            scalars[key] = tokens[1]

        elif key == "SOURCE":
            require(len(tokens) == 3, f"invalid Seed SOURCE binding: {line}")
            require(tokens[1] not in sources, f"duplicate Seed source: {tokens[1]}")
            sources[tokens[1]] = tokens[2]

        elif key == "COMPANION":
            require(len(tokens) == 4, f"invalid Seed companion binding: {line}")
            require(
                tokens[1] not in companions,
                f"duplicate Seed companion: {tokens[1]}",
            )
            companions[tokens[1]] = (tokens[2], tokens[3])

    for key in (
        "RELEASE-TAG",
        "RELEASE-TREE",
        "RELEASE-ARCHIVE",
        "PROFILE-TREE",
        "PROFILE-ARCHIVE",
    ):
        require(key in scalars, f"Seed binding scalar missing: {key}")

    for key in (
        "RELEASE-TREE",
        "RELEASE-ARCHIVE",
        "PROFILE-TREE",
        "PROFILE-ARCHIVE",
    ):
        require(
            re.fullmatch(r"sha256:[0-9a-f]{64}", scalars[key]) is not None,
            f"invalid Seed digest scalar: {key}",
        )

    require(len(sources) == 10, "Seed binding source count mismatch")
    for relative, digest in sources.items():
        require(
            re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is not None,
            f"invalid Seed source digest: {relative}",
        )

    require(
        set(companions) == {"ENGLISH", "PYTHON"},
        "Seed companion binding surface mismatch",
    )
    for role, (_, digest) in companions.items():
        require(
            re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is not None,
            f"invalid Seed companion digest: {role}",
        )

    return SeedBinding(
        release_tag=scalars["RELEASE-TAG"],
        release_tree=scalars["RELEASE-TREE"],
        release_archive=scalars["RELEASE-ARCHIVE"],
        profile_tree=scalars["PROFILE-TREE"],
        profile_archive=scalars["PROFILE-ARCHIVE"],
        companions=companions,
        sources=sources,
    )


def parse_sources() -> dict[str, str]:
    return dict(parse_seed_binding().sources)


def validate_seed_release_root(
    seed_release_root: Path,
    binding: SeedBinding,
) -> None:
    seed_release_root = seed_release_root.resolve()
    require(seed_release_root.is_dir(), "Seed release root missing")
    require(
        (seed_release_root / "RELEASE_MANIFEST.json").is_file(),
        "Seed release manifest missing",
    )
    require(
        tree_digest(seed_release_root) == binding.release_tree,
        "Seed release tree digest mismatch",
    )


def validate_seed_profiles_root(
    seed_profiles_root: Path,
    binding: SeedBinding,
) -> int:
    seed_profiles_root = seed_profiles_root.resolve()
    require(seed_profiles_root.is_dir(), "Seed profiles root missing")
    require(
        (seed_profiles_root / "RELEASE_PROFILE_MANIFEST.json").is_file(),
        "Seed release profile manifest missing",
    )
    require(
        tree_digest(seed_profiles_root) == binding.profile_tree,
        "Seed profile tree digest mismatch",
    )

    checked = 0
    for role, (relative, expected) in sorted(binding.companions.items()):
        path = seed_profiles_root / relative
        require(path.is_file(), f"Seed companion missing: {role}")
        require(sha256(path) == expected, f"Seed companion digest mismatch: {role}")
        checked += 1

    return checked


def validate_seed_root(seed_root: Path, sources: dict[str, str]) -> None:
    for rel, expected in sources.items():
        path = seed_root / rel
        require(path.is_file(), f"Seed source missing: {rel}")
        require(sha256(path) == expected, f"Seed source digest mismatch: {rel}")
    seed_subject = (seed_root / "seed/alpha4/SEED.aset").read_text(encoding="utf-8")
    require(
        "ASET-SEED 1 ASET-SEED-0.4-ALPHA 0.4alpha" in seed_subject,
        "Seed Alpha4 subject mismatch",
    )
    required_pair = (
        "PAIR ASET-COMPONENT-OBSERVE-UNKNOWN OBSERVE-UNKNOWN "
        "ObserveUnknown ObserveUnknownPairing"
    )
    require(
        required_pair in seed_subject,
        "Seed OBSERVE-UNKNOWN pair unavailable",
    )


def validate_subject() -> None:
    lines = nonempty(SUBJECT)
    require(
        lines[0] == "ASET-REVISION 1 ASET-REVISION-0.4-ALPHA 0.4alpha",
        "subject identity mismatch",
    )
    require("SEMANTIC-PRECEDENCE NONE" in lines, "semantic precedence must be NONE")
    require(
        not any(line.startswith("COMPATIBILITY ") for line in lines),
        "subject compatibility surface must be absent",
    )
    pairs = [line for line in lines if line.startswith("PAIR ")]
    require(
        pairs
        == [
            "PAIR ASET-REVISION-COMPONENT-PROPOSE-REVISION "
            "PROPOSE-REVISION ProposeRevision ProposeRevisionPairing"
        ],
        "subject must bind exactly one component",
    )
    require(
        "REVISION-PROJECTION PROPOSE-REVISION OBSERVE-UNKNOWN" in nonempty(BINDING),
        "Seed projection declaration mismatch",
    )


def validate_core_surface() -> None:
    rel = REL.read_text(encoding="utf-8")
    op = OP.read_text(encoding="utf-8")
    forth = FORTH.read_text(encoding="utf-8")
    pair = PAIR.read_text(encoding="utf-8")
    compose = COMPOSE.read_text(encoding="utf-8")
    seed_projection = SEED_PROJECTION.read_text(encoding="utf-8")
    seed_proof = SEED_PROOF.read_text(encoding="utf-8")

    require("VARIABLE" not in rel, "relational core must not own TLA variable state")
    require(
        "StateType == SUBSET ProposalUniverse" in rel,
        "single proposal-set state missing",
    )
    require(
        rel.count("ProposeRevision(s, t, p) ==") == 1,
        "expected exactly one core relation",
    )
    require("p.target = p.transition.genesis" in rel, "target/genesis binding missing")
    require(
        "tr.fromState # tr.toState" in rel,
        "non-stutter revision constraint missing",
    )
    require("t = s \\cup {p}" in rel, "append-only state transition missing")

    relation_definitions = tuple(
        re.findall(
            r"(?m)^([A-Za-z][A-Za-z0-9_]*)"
            r"\s*(?:\([^)]*\))?\s*==",
            rel,
        )
    )
    require(
        relation_definitions
        == (
            "RevisionTransition",
            "RevisionTransitionUniverse",
            "Proposal",
            "ProposalUniverse",
            "StateType",
            "ProposeRevision",
        ),
        "relational definition surface drift",
    )

    definitions = re.findall(r"(?m)^:\s+([A-Z0-9-]+)\b", forth)
    require(
        definitions == ["PROPOSE-REVISION"],
        "operational source must define one word",
    )
    require(
        "VALID-PROPOSAL?" in forth
        and "FRESH-PROPOSAL?" in forth
        and "APPEND-PROPOSAL" in forth,
        "operational proposal guards/effect incomplete",
    )
    require(
        forth.strip()
        == (
            ": PROPOSE-REVISION  "
            "( proposals proposal -- proposals )  "
            "VALID-PROPOSAL? FRESH-PROPOSAL? APPEND-PROPOSAL ;"
        ),
        "operational source differs from exact Revision program",
    )

    require(
        "OperationalProposeRevision(s, t, p)" in op,
        "operational reflection missing",
    )
    require(
        "ProposeRevisionPairing" in pair and "OperationalRelationalPairing" in pair,
        "pairing proof missing",
    )
    require("RevisionProposalSafety" in compose, "composition proof missing")
    require(
        "Seed!ObserveUnknown" in seed_projection,
        "proposal is not projected to Seed observation",
    )
    require(
        'recognition |-> "UNKNOWN"' in seed_projection,
        "Seed projection must remain UNKNOWN",
    )
    require(
        "RecognitionTheory == INSTANCE RecognitionCardinality" in seed_projection
        and "RecognitionTheory!EffectPermitted" in seed_projection,
        "Seed projection effect criterion must use exact pinned recognition theory",
    )
    require(
        "RevisionProposalPreservesSeedRecognitionBoundary" in seed_proof,
        "Seed boundary theorem missing",
    )
    require(
        "~ProjectedSeedEffectPermitted(p)" in seed_proof,
        "effect-permission exclusion theorem missing",
    )


def validate_causal() -> None:
    lines = nonempty(CAUSAL)
    require(
        lines[0] == "ASET-CAUSAL-NET 1 ASET-REVISION-0.4-ALPHA-CAUSAL",
        "causal identity mismatch",
    )
    require(
        "INVARIANT PROPOSAL-MEMBERSHIP-ONEHOT A P TOTAL 1" in lines,
        "causal one-hot invariant missing",
    )
    require(
        lines.count(
            "TRANSITION PROPOSE-REVISION ASET-REVISION-COMPONENT-PROPOSE-REVISION"
        )
        == 1,
        "causal transition count mismatch",
    )
    for expected in (
        "REQUIRE VALID_PROPOSAL",
        "REQUIRE FRESH_PROPOSAL",
        "EFFECT APPEND_PROPOSAL",
    ):
        require(expected in lines, f"causal semantics incomplete: {expected}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-root", type=Path)
    args = parser.parse_args()
    validate_subject()
    validate_core_surface()
    validate_causal()
    sources = parse_sources()
    require(len(sources) == 10, "Seed binding source count mismatch")
    if args.seed_root is not None:
        validate_seed_root(args.seed_root.resolve(), sources)
        print("ALPHA4_REVISION_SEED_CONTENT_BINDING=PASS")
    else:
        print("ALPHA4_REVISION_SEED_CONTENT_BINDING=DECLARED")
    print("ALPHA4_REVISION_SINGLE_STATE=PROPOSALS")
    print("ALPHA4_REVISION_SINGLE_TRANSITION=PROPOSE-REVISION")
    print("ALPHA4_REVISION_STATE_SURFACE=PROPOSALS_ONLY")
    print("ALPHA4_REVISION_SEED_PROJECTION=OBSERVE-UNKNOWN")
    print("ALPHA4_REVISION_VALIDATION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
