#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REPOSITORY_URL = "https://github.com/attractor-set/aset-revision"

IGNORED_ROOT_DIRS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".tlacache",
    ".tooling",
    ".venv",
    "__pycache__",
    "dist",
}

ALLOWED_ACTIVE_PATHS = set(
    [
        ".editorconfig",
        ".gitattributes",
        ".github/workflows/verify.yml",
        ".gitignore",
        "CITATION.cff",
        "LICENSE",
        "NOTICE",
        "README.md",
        "pyproject.toml",
        "requirements-ci.txt",
        "revision/alpha4/REVISION.aset",
        "revision/alpha4/causal/components.petri",
        "revision/alpha4/formal/ComponentCompositionProofs.tla",
        "revision/alpha4/formal/OperationalRelationalPairingProofs.tla",
        "revision/alpha4/formal/RestrictedOperationalSemantics.tla",
        "revision/alpha4/formal/RevisionRelations.tla",
        "revision/alpha4/formal/SeedProjection.tla",
        "revision/alpha4/formal/SeedProjectionProofs.tla",
        "revision/alpha4/operational/components.forth",
        "tests/test_alpha4_revision.py",
        "tests/test_alpha4_revision_release_profiles.py",
        "tools/__init__.py",
        "tools/alpha4_revision_expression_airgap_verifier.py",
        "tools/alpha4_revision_gate.py",
        "tools/alpha4_revision_paired_expression.py",
        "tools/alpha4_revision_public_release_audit.py",
        "tools/alpha4_revision_python_sqlite_persistence_gate.py",
        "tools/alpha4_revision_release_admission_certificate.py",
        "tools/alpha4_revision_release_gate.py",
        "tools/alpha4_revision_release_profile_congruence.py",
        "tools/alpha4_revision_release_profiles.py",
        "tools/build_alpha4_revision_release.py",
        "tools/run_alpha4_revision_tlaps.py",
        "tools/validate_alpha4_revision.py",
        "tools/validate_repository_minimal.py",
        "upstream/ASET_SEED_ALPHA4_BINDING.aset",
    ]
)

ALLOWED_ROOT_FILES = {path for path in ALLOWED_ACTIVE_PATHS if "/" not in path}

ALLOWED_ROOT_DIRS = {
    path.split("/", 1)[0] for path in ALLOWED_ACTIVE_PATHS if "/" in path
}


def filesystem_visible_files() -> set[str]:
    result: set[str] = set()

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(ROOT)

        if any(part in IGNORED_ROOT_DIRS for part in relative.parts):
            continue

        result.add(relative.as_posix())

    return result


def version_control_visible_files() -> set[str]:
    if not (ROOT / ".git").exists():
        return filesystem_visible_files()

    result = subprocess.run(
        [
            "git",
            "ls-files",
            "--cached",
            "--others",
            "--exclude-standard",
            "-z",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )

    if result.returncode:
        raise RuntimeError("git ls-files failed while resolving active surface")

    visible: set[str] = set()

    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue

        relative = raw.decode("utf-8")
        parts = Path(relative).parts

        if any(part in IGNORED_ROOT_DIRS for part in parts):
            continue

        path = ROOT / relative

        if path.is_file() or path.is_symlink():
            visible.add(relative)

    return visible


def main() -> int:
    errors: list[str] = []

    try:
        active_files = version_control_visible_files()
    except (OSError, RuntimeError, UnicodeError) as error:
        print(f"REPOSITORY_MINIMALITY_ERROR={error}")
        print("REPOSITORY_ACTIVE_SURFACE=FAIL")
        return 1

    for relative in sorted(active_files - ALLOWED_ACTIVE_PATHS):
        errors.append(f"unexpected active file: {relative}")

    for relative in sorted(ALLOWED_ACTIVE_PATHS - active_files):
        errors.append(f"required active file missing: {relative}")

    root_files = {path for path in active_files if "/" not in path}

    root_dirs = {path.split("/", 1)[0] for path in active_files if "/" in path}

    if root_files != ALLOWED_ROOT_FILES:
        errors.append("root file surface drift")

    if root_dirs != ALLOWED_ROOT_DIRS:
        errors.append("root directory surface drift")

    if "revision" not in root_dirs:
        errors.append("Revision semantic root missing")

    if "revision/alpha4/REVISION.aset" not in active_files:
        errors.append("Revision subject missing")

    if "history" in root_dirs or (ROOT / "history").exists():
        errors.append("history surface present")

    revision_paths = {path for path in active_files if path.startswith("revision/")}

    if any(not path.startswith("revision/alpha4/") for path in revision_paths):
        errors.append("revision root must contain only alpha4 active surface")

    readmes = sorted(
        path
        for path in active_files
        if Path(path).name.startswith("README") and path.endswith(".md")
    )

    if readmes != ["README.md"]:
        errors.append(f"single README invariant failed: {readmes}")

    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")

    for required in (
        "ASET Revision",
        "Copyright 2026 Dzmitry Prychyna",
        "Attractor Set",
        "Original author and copyright holder: Dzmitry Prychyna.",
    ):
        if required not in notice:
            errors.append(f"NOTICE attribution missing: {required}")

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")

    for required in (
        'title: "ASET Revision"',
        'version: "0.4alpha"',
        'family-names: "Prychyna"',
        'given-names: "Dzmitry"',
        f'repository-code: "{REPOSITORY_URL}"',
        "license: Apache-2.0",
    ):
        if required not in citation:
            errors.append(f"CITATION identity missing: {required}")

    license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")

    if "Apache License" not in license_text or "Version 2.0" not in license_text:
        errors.append("LICENSE is not Apache-2.0")

    subject = (ROOT / "revision/alpha4/REVISION.aset").read_text(encoding="utf-8")

    if not subject.startswith("ASET-REVISION 1 ASET-REVISION-0.4-ALPHA 0.4alpha\n"):
        errors.append("Revision subject identity drift")

    if any(line.startswith("COMPATIBILITY ") for line in subject.splitlines()):
        errors.append("Revision subject compatibility surface present")

    workflows = sorted(
        path.rsplit("/", 1)[-1]
        for path in active_files
        if path.startswith(".github/workflows/") and path.endswith(".yml")
    )

    if workflows != ["verify.yml"]:
        errors.append("CI surface must contain only verify.yml")

    if errors:
        for error in errors:
            print(f"REPOSITORY_MINIMALITY_ERROR={error}")

        print("REPOSITORY_ACTIVE_SURFACE=FAIL")
        return 1

    print("REPOSITORY_ACTIVE_SURFACE=MINIMAL")
    print("REPOSITORY_HISTORY_SURFACE=ABSENT")
    print("REPOSITORY_COMPATIBILITY_ALIAS_SURFACE=ABSENT")
    print("REPOSITORY_COPYRIGHT_NOTICE=PASS")
    print("REPOSITORY_CITATION=PASS")
    print("REPOSITORY_LICENSE=APACHE-2.0")
    print("REPOSITORY_IDENTITY=ASET-REVISION")
    print("REPOSITORY_LOCATOR=https://github.com/attractor-set/aset-revision")
    print("REPOSITORY_SINGLE_ACTIVE_REVISION_LINE=0.4alpha")
    print("REPOSITORY_SINGLE_VERIFICATION_WORKFLOW=PASS")
    print("ASET_REVISION_REPOSITORY_MINIMAL=PASS")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
