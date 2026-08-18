from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Callable


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def execute_python(path: Path) -> dict[str, Any]:
    namespace: dict[str, Any] = {}
    source = path.read_text(encoding="utf-8")
    require("External release companion" in source, "Python companion boundary missing")
    exec(compile(source, str(path), "exec"), namespace)
    return namespace


def observe(call: Callable[[], object]) -> tuple[str, object | None]:
    try:
        return ("ok", call())
    except (TypeError, ValueError):
        return ("error", None)


def expected_apply(
    current: tuple[tuple[str, str, str, str], ...],
    candidate: tuple[str, str, str, str],
) -> tuple[tuple[str, str, str, str], ...]:
    target, genesis, from_state, to_state = candidate
    normalized = tuple(sorted(set(current)))
    if target != genesis or from_state == to_state:
        raise ValueError("invalid revision proposal")
    if candidate in normalized:
        raise ValueError("revision proposal is not fresh")
    return tuple(sorted((*normalized, candidate)))


def subsets(
    values: tuple[tuple[str, str, str, str], ...],
) -> tuple[tuple[tuple[str, str, str, str], ...], ...]:
    result = []
    for mask in range(1 << len(values)):
        result.append(
            tuple(values[index] for index in range(len(values)) if mask & (1 << index))
        )
    return tuple(result)


def check_expression(expression: Path) -> dict[str, Any]:
    namespace = execute_python(expression)
    apply = namespace.get("propose_revision")
    require(callable(apply), "generated Python propose_revision missing")
    require(
        namespace.get("SEMANTIC_PRECEDENCE") == "NONE",
        "Python semantic precedence drift",
    )
    require(
        namespace.get("SEED_PROJECTION") == "OBSERVE-UNKNOWN",
        "Python Seed projection drift",
    )
    require(
        namespace.get("TERMINAL_RECOGNITION_OWNED") is False,
        "Python acquired recognition ownership",
    )
    require(
        namespace.get("EFFECT_PERMISSION_OWNED") is False,
        "Python acquired effect permission ownership",
    )

    contexts = ("context-a", "context-b")
    roots = ("root-0", "root-1", "root-2")
    valid = tuple(
        (target, genesis, source, target_root)
        for target, genesis, source, target_root in itertools.product(
            contexts, contexts, roots, roots
        )
        if target == genesis and source != target_root
    )
    raw = tuple(itertools.product(contexts, contexts, roots, roots))
    states = subsets(valid)
    cases = 0
    for current in states:
        for candidate in raw:
            expected = observe(lambda c=current, p=candidate: expected_apply(c, p))
            actual = observe(lambda c=current, p=candidate: apply(c, p))
            require(
                actual == expected,
                "generated Python differs from independent bounded oracle",
            )
            cases += 1
    require(cases == 147456, f"unexpected Python air-gap case count: {cases}")
    return {
        "document_type": "aset-revision-python-expression-airgap-evidence",
        "project": "ASET Revision",
        "expression": {
            "path": expression.name,
            "sha256": "sha256:" + hashlib.sha256(expression.read_bytes()).hexdigest(),
        },
        "cases_checked": cases,
        "valid_proposals": len(valid),
        "states_checked": len(states),
        "semantic_precedence": "NONE",
        "seed_projection": "OBSERVE-UNKNOWN",
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expression", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    evidence = check_expression(args.expression.resolve())
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    cases = evidence["cases_checked"]
    print(f"ALPHA4_REVISION_PYTHON_AIRGAP_CASES={cases}/{cases} PASS")
    print("ALPHA4_REVISION_PYTHON_SEMANTIC_PRECEDENCE=NONE")
    print("ALPHA4_REVISION_PYTHON_SEED_PROJECTION=OBSERVE-UNKNOWN")
    print("ALPHA4_REVISION_PYTHON_EXPRESSION_AIRGAP=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
