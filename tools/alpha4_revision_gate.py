from __future__ import annotations

import argparse
from pathlib import Path

from tools.alpha4_revision_paired_expression import check_paired_expression
from tools.validate_alpha4_revision import (
    parse_seed_binding,
    validate_causal,
    validate_core_surface,
    validate_seed_profiles_root,
    validate_seed_release_root,
    validate_seed_root,
    validate_subject,
)
from tools.validate_repository_minimal import main as validate_repository_minimal


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-root", type=Path, required=True)
    parser.add_argument("--seed-release-root", type=Path, required=True)
    parser.add_argument("--seed-profiles-root", type=Path, required=True)
    args = parser.parse_args()

    validate_repository_minimal()
    validate_subject()
    validate_core_surface()
    validate_causal()

    binding = parse_seed_binding()
    validate_seed_root(args.seed_root.resolve(), binding.sources)
    validate_seed_release_root(args.seed_release_root.resolve(), binding)
    companions = validate_seed_profiles_root(
        args.seed_profiles_root.resolve(),
        binding,
    )

    evidence = check_paired_expression()

    print("ALPHA4_REVISION_SEED_CONTENT_BINDING=PASS")
    print("ALPHA4_REVISION_SEED_RELEASE_TREE_BINDING=PASS")
    print("ALPHA4_REVISION_SEED_PROFILE_TREE_BINDING=PASS")
    print(f"ALPHA4_REVISION_SEED_COMPANION_BINDINGS={companions}/2 PASS")
    print("ALPHA4_REVISION_SEED_COMMIT_AUTHORITY=ABSENT")
    print("ALPHA4_REVISION_CORE_SURFACE=PASS")
    print(f"ALPHA4_REVISION_PAIRED_CASES={evidence['cases_checked']}")
    print("ALPHA4_REVISION_GATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
