#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROJECT = "ASET Revision"
REPOSITORY = "https://github.com/attractor-set/aset-revision"
SEED_REPOSITORY = "https://github.com/attractor-set/aset-seed"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()

    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")

    return "sha256:" + digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path.name}: expected object")
    return value


def repository_locators(text: str) -> set[str]:
    return {
        value.removesuffix(".git")
        for value in re.findall(
            r"https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+",
            text,
        )
    }


def check_public_release(
    release_root: Path,
    profiles_root: Path,
    release_archive: Path,
    profiles_archive: Path,
    certificate_path: Path,
) -> dict[str, Any]:
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    for required in (
        'title: "ASET Revision"',
        'version: "0.4alpha"',
        'family-names: "Prychyna"',
        'given-names: "Dzmitry"',
        f'repository-code: "{REPOSITORY}"',
    ):
        require(required in citation, f"CITATION drift: {required}")

    require(
        "Copyright 2026 Dzmitry Prychyna" in notice,
        "NOTICE copyright drift",
    )

    require(
        "Attractor Set" in notice,
        "NOTICE attribution drift",
    )

    require(
        "Apache License" in license_text and "Version 2.0" in license_text,
        "LICENSE drift",
    )

    release = load(release_root / "RELEASE_MANIFEST.json")
    profiles = load(profiles_root / "RELEASE_PROFILE_MANIFEST.json")
    certificate = load(certificate_path)

    require(
        certificate.get("document_type")
        == "aset-revision-release-admission-certificate",
        "certificate type drift",
    )

    require(
        certificate.get("status") == "PASS",
        "certificate not PASS",
    )

    for value in (release, profiles, certificate):
        require(
            value.get("project") == PROJECT,
            "project identity drift",
        )

        require(
            value.get("repository") == REPOSITORY,
            "repository locator drift",
        )

    release_identity = certificate.get("release")
    profiles_identity = certificate.get("profiles")

    require(
        isinstance(release_identity, dict),
        "release certificate identity missing",
    )

    require(
        isinstance(profiles_identity, dict),
        "profiles certificate identity missing",
    )

    require(
        release_identity.get("tree_digest") == tree_digest(release_root),
        "release tree digest drift",
    )

    require(
        release_identity.get("archive_sha256") == sha256(release_archive),
        "release archive digest drift",
    )

    require(
        profiles_identity.get("tree_digest") == tree_digest(profiles_root),
        "profiles tree digest drift",
    )

    require(
        profiles_identity.get("archive_sha256") == sha256(profiles_archive),
        "profiles archive digest drift",
    )

    allowed = {
        REPOSITORY,
        SEED_REPOSITORY,
    }

    for relative in (
        "README.md",
        "CITATION.cff",
        ".github/workflows/verify.yml",
    ):
        surface = (ROOT / relative).read_text(encoding="utf-8")

        for locator in repository_locators(surface):
            repository_name = locator.rsplit("/", 1)[-1]

            if repository_name.startswith("aset-"):
                require(
                    locator in allowed,
                    f"unexpected ASET repository locator: {relative}",
                )

    return {
        "document_type": "aset-revision-public-release-audit",
        "project": PROJECT,
        "repository": REPOSITORY,
        "representation_id": "0.4alpha",
        "release_tree_digest": tree_digest(release_root),
        "profile_tree_digest": tree_digest(profiles_root),
        "release_archive_sha256": sha256(release_archive),
        "profile_archive_sha256": sha256(profiles_archive),
        "release_admission_certificate_sha256": sha256(certificate_path),
        "copyright_notice": "PASS",
        "citation": "PASS",
        "license": "Apache-2.0",
        "repository_locator": "EXACT",
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--release-root",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--profiles-root",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--release-archive",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--profiles-archive",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--certificate",
        type=Path,
        required=True,
    )

    parser.add_argument(
        "--output",
        type=Path,
        required=True,
    )

    args = parser.parse_args()

    evidence = check_public_release(
        args.release_root.resolve(),
        args.profiles_root.resolve(),
        args.release_archive.resolve(),
        args.profiles_archive.resolve(),
        args.certificate.resolve(),
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.output.write_text(
        json.dumps(
            evidence,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    print("ALPHA4_REVISION_PUBLIC_IDENTITY=PASS")
    print("ALPHA4_REVISION_COPYRIGHT_NOTICE=PASS")
    print("ALPHA4_REVISION_PUBLIC_RELEASE_AUDIT=PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
