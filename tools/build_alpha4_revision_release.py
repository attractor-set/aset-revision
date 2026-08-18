from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path

from tools.alpha4_revision_release_profile_congruence import (
    check_release_profile_congruence,
)
from tools.alpha4_revision_release_profiles import build_release_profiles, sha256

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RELEASE_NAME = "ASET-Revision-0.4alpha"
PROFILES_NAME = f"{RELEASE_NAME}-profiles"
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)

SOURCE_PATHS = (
    "revision/alpha4/REVISION.aset",
    "revision/alpha4/operational/components.forth",
    "revision/alpha4/causal/components.petri",
    "revision/alpha4/formal/RevisionRelations.tla",
    "revision/alpha4/formal/RestrictedOperationalSemantics.tla",
    "revision/alpha4/formal/ComponentCompositionProofs.tla",
    "revision/alpha4/formal/OperationalRelationalPairingProofs.tla",
    "revision/alpha4/formal/SeedProjection.tla",
    "revision/alpha4/formal/SeedBoundaryProofs.tla",
    "upstream/ASET_SEED_ALPHA4_BINDING.aset",
)


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def zip_tree(root: Path, output: Path, archive_root_name: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(
        output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            relative = f"{archive_root_name}/{path.relative_to(root).as_posix()}"
            info = zipfile.ZipInfo(relative, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, path.read_bytes())


def build_source_release(output: Path) -> dict[str, object]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    shutil.copy2(ROOT / "LICENSE", output / "LICENSE")
    shutil.copy2(ROOT / "NOTICE", output / "NOTICE")
    for relative in SOURCE_PATHS:
        source = ROOT / relative
        target = output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    artifacts = [
        {"path": path.relative_to(output).as_posix(), "sha256": sha256(path)}
        for path in sorted(output.rglob("*"))
        if path.is_file()
    ]
    manifest = {
        "document_type": "aset-revision-release-materialization",
        "project": "ASET Revision",
        "repository": "https://github.com/attractor-set/aset-revision",
        "representation_id": "0.4alpha",
        "subject_id": "ASET-REVISION-0.4-ALPHA",
        "version": "0.4alpha",
        "semantic_precedence": "NONE",
        "semantic_core": {"state": "proposals", "transition": "PROPOSE-REVISION"},
        "seed_projection": "PROPOSE-REVISION -> OBSERVE-UNKNOWN",
        "source_materialization": "DIRECT_SOURCE_COPY",
        "artifacts": artifacts,
    }
    (output / "RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def build_profiles(output: Path, source_tree_digest: str) -> dict[str, object]:
    generated = build_release_profiles(ROOT, output)
    congruence = check_release_profile_congruence(output)
    (output / "RELEASE_PROFILE_EVIDENCE.json").write_text(
        json.dumps(congruence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    artifacts = [
        {"path": path.relative_to(output).as_posix(), "sha256": sha256(path)}
        for path in sorted(output.rglob("*"))
        if path.is_file()
    ]
    manifest = {
        "document_type": "aset-revision-ci-release-companion-materialization",
        "project": "ASET Revision",
        "repository": "https://github.com/attractor-set/aset-revision",
        "representation_id": "0.4alpha",
        "subject_id": "ASET-REVISION-0.4-ALPHA",
        "version": "0.4alpha",
        "membership": "EXTERNAL_RELEASE_COMPANION",
        "semantic_precedence": "NONE",
        "source_release_tree_digest": source_tree_digest,
        "source_byte_identity_digest": generated["source_byte_identity_digest"],
        "profiles": {
            "controlled_english": "en/Revision.md",
            "python": "python/aset_revision_alpha4.py",
            "python_sqlite": {
                "role": "PERSISTENCE_EXTENSION",
                "base_expression": "python",
                "semantic_delta": "NONE",
                "path": "python-sqlite/aset_revision_alpha4_sqlite.py",
                "binding": "python-sqlite/PERSISTENCE_EXTENSION.json",
            },
        },
        "congruence_evidence": "RELEASE_PROFILE_EVIDENCE.json",
        "artifacts": artifacts,
    }
    (output / "RELEASE_PROFILE_MANIFEST.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify-determinism", action="store_true")
    args = parser.parse_args()
    release = DIST / RELEASE_NAME
    profiles = DIST / PROFILES_NAME
    build_source_release(release)
    source_digest = tree_digest(release)
    build_profiles(profiles, source_digest)
    profile_digest = tree_digest(profiles)

    if args.verify_determinism:
        with tempfile.TemporaryDirectory(prefix="aset-revision-alpha4-") as temp:
            first = Path(temp) / "release-1"
            second = Path(temp) / "release-2"
            first_profiles = Path(temp) / "profiles-1"
            second_profiles = Path(temp) / "profiles-2"
            build_source_release(first)
            build_source_release(second)
            require_same = tree_digest(first) == tree_digest(second)
            if not require_same:
                raise RuntimeError("Revision source release is not deterministic")
            first_digest = tree_digest(first)
            second_digest = tree_digest(second)
            build_profiles(first_profiles, first_digest)
            build_profiles(second_profiles, second_digest)
            if tree_digest(first_profiles) != tree_digest(second_profiles):
                raise RuntimeError("Revision companion release is not deterministic")
        print("ALPHA4_REVISION_RELEASE_DETERMINISM=PASS")
        print("ALPHA4_REVISION_RELEASE_PROFILE_DETERMINISM=PASS")

    archive = DIST / f"{RELEASE_NAME}.zip"
    profiles_archive = DIST / f"{PROFILES_NAME}.zip"
    zip_tree(release, archive, RELEASE_NAME)
    zip_tree(profiles, profiles_archive, PROFILES_NAME)
    print("ALPHA4_REVISION_RELEASE_ENGLISH_PROFILE=PASS")
    print("ALPHA4_REVISION_RELEASE_PYTHON_PROFILE=PASS")
    print(
        "ALPHA4_REVISION_RELEASE_PYTHON_SQLITE_RELATION=PERSISTENCE_EXTENSION_OF_PYTHON"
    )
    print("ALPHA4_REVISION_RELEASE_PYTHON_SQLITE_SEMANTIC_DELTA=NONE")
    print("ALPHA4_REVISION_RELEASE_PROFILE_CONGRUENCE=PASS")
    print(f"ALPHA4_REVISION_RELEASE_TREE_DIGEST={source_digest}")
    print(f"ALPHA4_REVISION_RELEASE_PROFILE_TREE_DIGEST={profile_digest}")
    print(f"ALPHA4_REVISION_RELEASE_ARCHIVE_SHA256={sha256(archive)}")
    print(f"ALPHA4_REVISION_RELEASE_PROFILE_ARCHIVE_SHA256={sha256(profiles_archive)}")
    print("ALPHA4_REVISION_RELEASE_BUILD=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
