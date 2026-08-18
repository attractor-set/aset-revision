from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORMAL = ROOT / "revision/alpha4/formal"
PROOFS = (
    (
        "COMPONENT_COMPOSITION",
        FORMAL / "ComponentCompositionProofs.tla",
        "RevisionProposalSafety",
        False,
    ),
    (
        "OPERATIONAL_RELATIONAL_PAIRING",
        FORMAL / "OperationalRelationalPairingProofs.tla",
        "OperationalRelationalPairing",
        False,
    ),
    (
        "SEED_PROJECTION",
        FORMAL / "SeedProjectionProofs.tla",
        "RevisionProposalPreservesSeedRecognitionBoundary",
        True,
    ),
)


def default_tlapm() -> str:
    return os.environ.get("TLAPM_BIN", str(ROOT / ".tooling/tlapm/bin/tlapm"))


def obligations(text: str) -> int | None:
    match = re.search(r"All\s+(\d+)\s+obligations\s+proved\.", text)
    return int(match.group(1)) if match else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tlapm", default=default_tlapm())
    parser.add_argument("--seed-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    seed_root = args.seed_root.resolve()
    include = [
        "-I",
        str(FORMAL),
        "-I",
        str(seed_root / "seed/alpha4/formal"),
        "-I",
        str(seed_root / "theory/local-recognition/formal"),
    ]
    total = 0
    proof_evidence: list[dict[str, object]] = []
    print("ALPHA4_REVISION_TLAPS=START")
    for proof_id, path, theorem, needs_seed in PROOFS:
        seed_relations = seed_root / "seed/alpha4/formal/ComponentRelations.tla"
        if needs_seed and not seed_relations.is_file():
            print("ALPHA4_REVISION_TLAPS_ERROR=Seed ComponentRelations.tla missing")
            print("ALPHA4_REVISION_TLAPS=FAIL")
            return 1
        print(f"ALPHA4_REVISION_TLAPS_SUBJECT={proof_id}:START")
        print(f"ALPHA4_REVISION_TLAPS_MODULE={path.name}")
        print(f"ALPHA4_REVISION_TLAPS_FINAL_THEOREM={theorem}")
        try:
            result = subprocess.run(
                [args.tlapm, *include, str(path)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError as error:
            print(f"ALPHA4_REVISION_TLAPS_ERROR={type(error).__name__}: {error}")
            print("ALPHA4_REVISION_TLAPS=FAIL")
            return 1
        if result.stdout:
            sys.stdout.write(result.stdout)
        if result.stderr:
            sys.stderr.write(result.stderr)
        count = obligations(result.stdout + "\n" + result.stderr)
        if result.returncode != 0 or count is None or count <= 0:
            print(f"ALPHA4_REVISION_TLAPS_OBLIGATIONS={count}")
            print(f"ALPHA4_REVISION_TLAPS_SUBJECT={proof_id}:FAIL")
            print("ALPHA4_REVISION_TLAPS=FAIL")
            return result.returncode or 1
        total += count
        proof_evidence.append(
            {
                "id": proof_id,
                "path": path.relative_to(ROOT).as_posix(),
                "sha256": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
                "final_theorem": theorem,
                "obligations": count,
                "status": "PASS",
            }
        )
        print(f"ALPHA4_REVISION_TLAPS_OBLIGATIONS={count}")
        print(f"ALPHA4_REVISION_TLAPS_SUBJECT={proof_id}:PASS")
    if total != 30:
        print(f"ALPHA4_REVISION_TLAPS_ERROR=unexpected total obligations: {total}")
        print("ALPHA4_REVISION_TLAPS=FAIL")
        return 1
    if args.output is not None:
        evidence = {
            "document_type": "aset-revision-alpha4-tlaps-evidence",
            "project": "ASET Revision",
            "subject_id": "ASET-REVISION-0.4-ALPHA",
            "representation_id": "0.4alpha",
            "semantic_precedence": "NONE",
            "seed_binding": {
                "path": "upstream/ASET_SEED_ALPHA4_BINDING.aset",
                "sha256": "sha256:"
                + hashlib.sha256(
                    (ROOT / "upstream/ASET_SEED_ALPHA4_BINDING.aset").read_bytes()
                ).hexdigest(),
            },
            "proofs": proof_evidence,
            "total_obligations": total,
            "status": "PASS",
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(f"ALPHA4_REVISION_TLAPS_TOTAL_OBLIGATIONS={total}")
    print("ALPHA4_REVISION_TLAPS=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
