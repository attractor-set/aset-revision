from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RELEASE = DIST / "ASET-Revision-0.4alpha"
PROFILES = DIST / "ASET-Revision-0.4alpha-profiles"
RELEASE_ARCHIVE = DIST / "ASET-Revision-0.4alpha.zip"
PROFILES_ARCHIVE = DIST / "ASET-Revision-0.4alpha-profiles.zip"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-root", type=Path, required=True)
    parser.add_argument("--seed-release-root", type=Path, required=True)
    parser.add_argument("--seed-profiles-root", type=Path, required=True)
    parser.add_argument("--tlapm")
    args = parser.parse_args()
    seed_root = args.seed_root.resolve()
    seed_release_root = args.seed_release_root.resolve()
    seed_profiles_root = args.seed_profiles_root.resolve()
    tlapm = args.tlapm or os.environ.get(
        "TLAPM_BIN", str(seed_root / ".tooling/tlapm/bin/tlapm")
    )
    commands = [
        [
            sys.executable,
            "-m",
            "tools.alpha4_revision_gate",
            "--seed-root",
            str(seed_root),
            "--seed-release-root",
            str(seed_release_root),
            "--seed-profiles-root",
            str(seed_profiles_root),
        ],
        [
            sys.executable,
            "-m",
            "tools.run_alpha4_revision_tlaps",
            "--seed-root",
            str(seed_root),
            "--tlapm",
            tlapm,
            "--output",
            "dist/tlaps-evidence.json",
        ],
        [
            sys.executable,
            "-m",
            "tools.build_alpha4_revision_release",
            "--verify-determinism",
        ],
        [
            sys.executable,
            "-m",
            "tools.alpha4_revision_expression_airgap_verifier",
            "--expression",
            "dist/ASET-Revision-0.4alpha-profiles/python/aset_revision_alpha4.py",
            "--output",
            "dist/python-expression-airgap-evidence.json",
        ],
        [
            sys.executable,
            "-m",
            "tools.alpha4_revision_python_sqlite_persistence_gate",
            "--profiles-root",
            "dist/ASET-Revision-0.4alpha-profiles",
            "--output",
            "dist/python-sqlite-persistence-evidence.json",
        ],
        [
            sys.executable,
            "-m",
            "tools.alpha4_revision_release_admission_certificate",
            "--tlaps-evidence",
            "dist/tlaps-evidence.json",
            "--expression-evidence",
            "dist/python-expression-airgap-evidence.json",
            "--persistence-evidence",
            "dist/python-sqlite-persistence-evidence.json",
            "--release-root",
            str(RELEASE.relative_to(ROOT)),
            "--profiles-root",
            str(PROFILES.relative_to(ROOT)),
            "--release-archive",
            str(RELEASE_ARCHIVE.relative_to(ROOT)),
            "--profiles-archive",
            str(PROFILES_ARCHIVE.relative_to(ROOT)),
            "--output",
            "dist/release-admission-certificate.json",
        ],
        [
            sys.executable,
            "-m",
            "tools.alpha4_revision_public_release_audit",
            "--release-root",
            str(RELEASE.relative_to(ROOT)),
            "--profiles-root",
            str(PROFILES.relative_to(ROOT)),
            "--release-archive",
            str(RELEASE_ARCHIVE.relative_to(ROOT)),
            "--profiles-archive",
            str(PROFILES_ARCHIVE.relative_to(ROOT)),
            "--certificate",
            "dist/release-admission-certificate.json",
            "--output",
            "dist/public-release-audit.json",
        ],
    ]
    for command in commands:
        result = subprocess.run(command, cwd=ROOT, check=False)
        if result.returncode:
            print("ALPHA4_REVISION_RELEASE_GATE=FAIL")
            return result.returncode
    print("ALPHA4_REVISION_RELEASE_GATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
