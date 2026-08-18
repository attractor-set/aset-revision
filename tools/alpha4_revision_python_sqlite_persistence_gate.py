from __future__ import annotations

import argparse
import hashlib
import importlib.util
import itertools
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def execute_python(path: Path) -> dict[str, Any]:
    namespace: dict[str, Any] = {}
    exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), namespace)
    return namespace


def execute_extension(path: Path) -> dict[str, Any]:
    spec = importlib.util.spec_from_file_location("aset_revision_alpha4_sqlite", path)
    require(
        spec is not None and spec.loader is not None,
        "SQLite extension cannot be loaded",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return vars(module)


def observe(call: Callable[[], object]) -> tuple[str, object | None]:
    try:
        return ("ok", call())
    except (sqlite3.IntegrityError, TypeError, ValueError):
        return ("error", None)


def subsets(
    values: tuple[tuple[str, str, str, str], ...],
) -> tuple[tuple[tuple[str, str, str, str], ...], ...]:
    result = []
    for mask in range(1 << len(values)):
        result.append(
            tuple(values[index] for index in range(len(values)) if mask & (1 << index))
        )
    return tuple(result)


def check_persistence(profiles_root: Path) -> dict[str, Any]:
    before = tree_digest(profiles_root)
    binding_path = profiles_root / "python-sqlite/PERSISTENCE_EXTENSION.json"
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    require(binding.get("relation") == "PERSISTENCE_EXTENSION", "SQLite relation drift")
    require(binding.get("semantic_delta") == "NONE", "SQLite semantic delta drift")
    require(
        binding.get("semantic_precedence") == "NONE",
        "SQLite semantic precedence drift",
    )
    base_path = profiles_root / str(binding["base_expression"]["path"])
    extension_path = profiles_root / str(binding["extension"]["path"])
    require(
        sha256(base_path) == binding["base_expression"]["sha256"],
        "base Python bytes differ",
    )
    require(
        sha256(extension_path) == binding["extension"]["sha256"],
        "SQLite extension bytes differ",
    )

    old = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        base = execute_python(base_path)
        extension = execute_extension(extension_path)
    finally:
        sys.dont_write_bytecode = old
    apply = base.get("propose_revision")
    store_type = extension.get("SQLiteStore")
    require(callable(apply) and callable(store_type), "companion entry points missing")

    contexts = ("context-a", "context-b")
    roots = ("root-0", "root-1", "root-2")
    valid = tuple(
        (target, genesis, source_root, target_root)
        for target, genesis, source_root, target_root in itertools.product(
            contexts, contexts, roots, roots
        )
        if target == genesis and source_root != target_root
    )
    raw = tuple(itertools.product(contexts, contexts, roots, roots))
    exhaustive_states = subsets(valid)
    states = tuple(
        state
        for state in exhaustive_states
        if len(state) <= 2 or len(state) == len(valid)
    )

    cases = 0
    rollback_checks = 0
    restart_checks = 0
    with tempfile.TemporaryDirectory(prefix="aset-revision-sqlite-") as temp:
        database = Path(temp) / "revision.sqlite3"
        store = store_type(database)

        with sqlite3.connect(database) as connection:
            tables = tuple(
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
                )
            )
            require(
                tables == ("proposals",),
                "SQLite table surface drift",
            )

            columns = tuple(
                row[1] for row in connection.execute("PRAGMA table_info(proposals)")
            )
            require(
                columns
                == (
                    "target",
                    "genesis",
                    "from_state",
                    "to_state",
                ),
                "SQLite proposal schema drift",
            )
        for state_index, current in enumerate(states):
            for candidate_index, candidate in enumerate(raw):
                store.replace(current)
                before_state = store.load()
                expected = observe(lambda c=current, p=candidate: apply(c, p))
                actual = observe(lambda p=candidate: store.propose_revision(p))
                require(
                    actual == expected,
                    "SQLite persistence differs from exact Python expression",
                )
                if actual[0] == "ok":
                    if restart_checks < 12:
                        reopened = store_type(database)
                        require(
                            reopened.load() == actual[1],
                            "committed proposal did not survive restart",
                        )
                        restart_checks += 1
                else:
                    require(
                        store_type(database).load() == before_state,
                        "rejected proposal changed persistent state",
                    )
                    rollback_checks += 1
                cases += 1
    expected_cases = len(states) * len(raw)
    require(
        cases == expected_cases,
        f"unexpected SQLite congruence case count: {cases}",
    )
    require(len(states) == 80, f"unexpected SQLite state surface: {len(states)}")
    require(rollback_checks > 0, "SQLite rollback path not exercised")
    require(restart_checks > 0, "SQLite restart path not exercised")
    after = tree_digest(profiles_root)
    require(before == after, "SQLite gate mutated release profiles")
    return {
        "document_type": "aset-revision-python-sqlite-persistence-evidence",
        "project": "ASET Revision",
        "relation": "PERSISTENCE_EXTENSION_OF_EXACT_PYTHON_EXPRESSION",
        "base_expression_congruence_cases": cases,
        "rollback_checks": rollback_checks,
        "restart_round_trip_checks": restart_checks,
        "semantic_delta": "NONE",
        "semantic_precedence": "NONE",
        "schema_semantic_fields": ["proposals"],
        "base_expression_binding": {
            "path": str(binding["base_expression"]["path"]),
            "sha256": sha256(base_path),
        },
        "extension_binding": {
            "path": str(binding["extension"]["path"]),
            "sha256": sha256(extension_path),
        },
        "materialization_boundary": {
            "profile_tree_unchanged": True,
            "python_bytecode_written": False,
        },
        "profile_tree_unchanged": True,
        "status": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    evidence = check_persistence(args.profiles_root.resolve())
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    cases = evidence["base_expression_congruence_cases"]
    print(f"ALPHA4_REVISION_PYTHON_SQLITE_CONGRUENCE={cases}/{cases} PASS")
    print(
        "ALPHA4_REVISION_PYTHON_SQLITE_ROLLBACK_CHECKS="
        f"{evidence['rollback_checks']} PASS"
    )
    print(
        "ALPHA4_REVISION_PYTHON_SQLITE_RESTART_CHECKS="
        f"{evidence['restart_round_trip_checks']} PASS"
    )
    print("ALPHA4_REVISION_PYTHON_SQLITE_SEMANTIC_DELTA=NONE")
    print("ALPHA4_REVISION_PYTHON_SQLITE_PERSISTENCE_EXTENSION=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
