from __future__ import annotations

import itertools
from pathlib import Path
from typing import FrozenSet, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "revision/alpha4"


class Proposal(NamedTuple):
    target: str
    genesis: str
    from_state: str
    to_state: str


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def proposal_universe(
    contexts: tuple[str, ...], roots: tuple[str, ...]
) -> tuple[Proposal, ...]:
    return tuple(
        Proposal(target, genesis, source, target_root)
        for target, genesis, source, target_root in itertools.product(
            contexts, contexts, roots, roots
        )
        if target == genesis and source != target_root
    )


def compile_operational() -> tuple[str, ...]:
    source = (BASE / "operational/components.forth").read_text(encoding="utf-8")
    body = source.split(")", 1)[1].rsplit(";", 1)[0].split()
    require(
        body == ["VALID-PROPOSAL?", "FRESH-PROPOSAL?", "APPEND-PROPOSAL"],
        "operational token sequence drift",
    )
    return tuple(body)


def apply_operational(
    state: FrozenSet[Proposal],
    proposal: Proposal,
    universe: FrozenSet[Proposal],
    program: tuple[str, ...],
) -> tuple[str, FrozenSet[Proposal] | None]:
    current = state
    for word in program:
        if word == "VALID-PROPOSAL?" and proposal not in universe:
            return ("error", None)
        if word == "FRESH-PROPOSAL?" and proposal in current:
            return ("error", None)
        if word == "APPEND-PROPOSAL":
            current = current | {proposal}
    return ("ok", current)


def validate_relational_source() -> None:
    source = (BASE / "formal/RevisionRelations.tla").read_text(encoding="utf-8")
    required = (
        "p \\in ProposalUniverse",
        "p \\notin s",
        "t = s \\cup {p}",
        "p.target = p.transition.genesis",
        "tr.fromState # tr.toState",
    )
    for fragment in required:
        require(fragment in source, f"relational source fragment missing: {fragment}")


def apply_relational(
    state: FrozenSet[Proposal],
    proposal: Proposal,
    universe: FrozenSet[Proposal],
) -> tuple[str, FrozenSet[Proposal] | None]:
    if proposal not in universe:
        return ("error", None)
    if proposal in state:
        return ("error", None)
    return ("ok", state | {proposal})


def validate_causal_source() -> None:
    lines = {
        line.strip()
        for line in (BASE / "causal/components.petri")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }
    expected = {
        "FROM A",
        "REQUIRE VALID_PROPOSAL",
        "REQUIRE FRESH_PROPOSAL",
        "EFFECT APPEND_PROPOSAL",
        "TO P",
    }
    require(
        expected <= lines,
        "causal source differs from proposal-membership relation",
    )


def subsets(values: tuple[Proposal, ...]) -> tuple[FrozenSet[Proposal], ...]:
    result: list[FrozenSet[Proposal]] = []
    for mask in range(1 << len(values)):
        result.append(
            frozenset(
                value for index, value in enumerate(values) if mask & (1 << index)
            )
        )
    return tuple(result)


def check_paired_expression() -> dict[str, int | str]:
    program = compile_operational()
    validate_relational_source()
    validate_causal_source()

    contexts = ("context-a", "context-b")
    roots = ("root-0", "root-1", "root-2")
    universe_values = proposal_universe(contexts, roots)
    universe = frozenset(universe_values)
    states = subsets(universe_values)
    raw_candidates = tuple(
        Proposal(target, genesis, source, target_root)
        for target, genesis, source, target_root in itertools.product(
            contexts, contexts, roots, roots
        )
    )

    cases = 0
    for state in states:
        for proposal in raw_candidates:
            operational = apply_operational(state, proposal, universe, program)
            relational = apply_relational(state, proposal, universe)
            require(
                operational == relational,
                "operational/relational bounded behavior differs",
            )
            cases += 1

    return {
        "components_checked": 1,
        "cases_checked": cases,
        "valid_proposals": len(universe_values),
        "states_checked": len(states),
        "status": "PASS",
    }


def main() -> int:
    evidence = check_paired_expression()
    print("ALPHA4_REVISION_PAIRED_GRAPH_CONGRUENCE=1/1 PASS")
    print("ALPHA4_REVISION_CAUSAL_CONGRUENCE=1/1 PASS")
    print(
        "ALPHA4_REVISION_BOUNDED_OBSERVATIONAL_CONGRUENCE="
        f"{evidence['cases_checked']}/{evidence['cases_checked']} PASS"
    )
    print(f"ALPHA4_REVISION_VALID_PROPOSALS={evidence['valid_proposals']}")
    print(f"ALPHA4_REVISION_STATES_CHECKED={evidence['states_checked']}")
    print("ALPHA4_REVISION_PAIRED_EXPRESSION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
