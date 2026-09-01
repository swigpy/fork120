#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed FORK/120 state validation and CANON rendering."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


TOP_LEVEL_KEYS = {
    "version",
    "state_id",
    "rules_path",
    "bible_path",
    "chapter_id",
    "round",
    "settlement_kind",
    "parent",
    "world",
    "world_word_count",
    "pressure",
    "sources",
    "ledger_delta",
    "content_license",
    "created_at",
}
PARENT_KEYS = {"state_id", "git_commit", "activation_comment"}
LEDGER_KEYS = {"active", "transformed", "resolved", "dormant"}
STATE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-r[0-9]{3}$")
CHAPTER_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LEDGER_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
COMMENT_RE = re.compile(r"^c[1-9][0-9]*$")


class ValidationError(ValueError):
    """Raised when candidate state is not canonicalizable."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def word_count(text: str) -> int:
    """Count non-empty whitespace-delimited runs, as defined by game v0.1."""

    return len(re.findall(r"\S+", text))


def _validate_pinned_path(repo_root: Path, value: Any, prefix: str, field: str) -> None:
    _require(isinstance(value, str), f"{field} must be a string")
    path = PurePosixPath(value)
    _require(not path.is_absolute(), f"{field} must be repository-relative")
    _require(".." not in path.parts and "." not in path.parts, f"{field} may not traverse")
    _require(value.startswith(prefix + "/") and value.endswith(".md"), f"{field} has invalid scope")
    resolved = repo_root.joinpath(*path.parts)
    _require(resolved.is_file(), f"{field} does not exist: {value}")


def _validate_timestamp(value: Any) -> None:
    _require(isinstance(value, str), "created_at must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("created_at must be ISO-8601") from exc
    _require(parsed.tzinfo is not None, "created_at must include a timezone")


def validate_state(state: Any, repo_root: Path, state_path: Path | None = None) -> None:
    """Validate one closed v1 state and all invariants not expressible in JSON Schema."""

    _require(isinstance(state, dict), "state must be an object")
    keys = set(state)
    _require(keys == TOP_LEVEL_KEYS, f"closed state keys differ: {sorted(keys ^ TOP_LEVEL_KEYS)}")
    _require(type(state["version"]) is int and state["version"] == 1, "version must equal integer 1")

    state_id = state["state_id"]
    _require(isinstance(state_id, str) and STATE_ID_RE.fullmatch(state_id) is not None, "invalid state_id")
    if state_path is not None:
        _require(state_path.stem == state_id, "state filename must equal state_id")

    _validate_pinned_path(repo_root, state["rules_path"], "rules", "rules_path")
    _validate_pinned_path(repo_root, state["bible_path"], "world", "bible_path")

    chapter_id = state["chapter_id"]
    _require(isinstance(chapter_id, str) and CHAPTER_ID_RE.fullmatch(chapter_id) is not None, "invalid chapter_id")
    round_number = state["round"]
    _require(type(round_number) is int and round_number >= 0, "round must be a non-negative integer")
    kind = state["settlement_kind"]
    _require(kind in {"GENESIS", "MOVES", "PRESSURE"}, "invalid settlement_kind")

    parent = state["parent"]
    if round_number == 0:
        _require(kind == "GENESIS", "round zero must be GENESIS")
        _require(parent is None, "GENESIS parent must be null")
    else:
        _require(kind != "GENESIS", "GENESIS is only valid at round zero")
        _require(isinstance(parent, dict) and set(parent) == PARENT_KEYS, "non-genesis parent must be closed")
        _require(isinstance(parent["state_id"], str) and STATE_ID_RE.fullmatch(parent["state_id"]) is not None, "invalid parent state_id")
        _require(isinstance(parent["git_commit"], str) and COMMIT_RE.fullmatch(parent["git_commit"]) is not None, "invalid parent git_commit")
        _require(isinstance(parent["activation_comment"], str) and COMMENT_RE.fullmatch(parent["activation_comment"]) is not None, "invalid parent activation_comment")

    world = state["world"]
    _require(isinstance(world, str) and world != "", "world must be a non-empty string")
    _require(world == world.strip(), "world may not have leading or trailing whitespace")
    measured = word_count(world)
    declared = state["world_word_count"]
    _require(type(declared) is int, "world_word_count must be an integer")
    _require(measured == declared, f"world_word_count mismatch: declared {declared}, measured {measured}")
    _require(measured <= 120, f"world must contain at most 120 words, measured {measured}")

    pressure = state["pressure"]
    _require(isinstance(pressure, str) and pressure == pressure.strip() and pressure != "", "pressure must be trimmed and non-empty")

    sources = state["sources"]
    _require(isinstance(sources, list), "sources must be an array")
    _require(all(isinstance(item, str) and COMMENT_RE.fullmatch(item) is not None for item in sources), "invalid source comment id")
    _require(len(sources) == len(set(sources)), "sources must be unique")
    if kind == "MOVES":
        _require(len(sources) >= 1, "MOVES settlement requires a source")
    else:
        _require(sources == [], f"{kind} settlement may not contain move sources")

    ledger = state["ledger_delta"]
    _require(isinstance(ledger, dict) and set(ledger) == LEDGER_KEYS, "ledger_delta must be closed")
    all_ids: list[str] = []
    for status in ("active", "transformed", "resolved", "dormant"):
        values = ledger[status]
        _require(isinstance(values, list), f"ledger_delta.{status} must be an array")
        _require(all(isinstance(item, str) and LEDGER_ID_RE.fullmatch(item) is not None for item in values), f"invalid ledger id in {status}")
        _require(len(values) == len(set(values)), f"duplicate ledger id within {status}")
        all_ids.extend(values)
    _require(len(all_ids) <= 12, "active ledger delta may contain at most twelve ids")
    _require(len(all_ids) == len(set(all_ids)), "ledger ids may occur in only one status")

    _require(state["content_license"] == "CC-BY-SA-4.0", "content_license must be CC-BY-SA-4.0")
    _validate_timestamp(state["created_at"])


def load_and_validate(path: Path, repo_root: Path) -> dict[str, Any]:
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse {path}: {exc}") from exc
    validate_state(state, repo_root, path)
    return state


def validate_schema(repo_root: Path) -> None:
    schema_path = repo_root / "canon" / "state.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse schema: {exc}") from exc
    _require(schema.get("additionalProperties") is False, "schema root must be closed")
    _require(set(schema.get("required", [])) == TOP_LEVEL_KEYS, "schema required keys differ from validator")
    _require(set(schema.get("properties", {})) == TOP_LEVEL_KEYS, "schema properties differ from validator")


def discover_states(repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in (repo_root / "canon" / "examples", repo_root / "canon" / "states"):
        if directory.is_dir():
            paths.extend(sorted(directory.glob("*.json")))
    return paths


def validate_repository(repo_root: Path) -> list[Path]:
    validate_schema(repo_root)
    states = discover_states(repo_root)
    _require(states != [], "repository contains no candidate states")
    for path in states:
        load_and_validate(path, repo_root)
    return states


def render_canon(state: dict[str, Any], git_commit: str) -> str:
    _require(COMMIT_RE.fullmatch(git_commit) is not None, "git commit must be 40 lowercase hex characters")
    parent = state["parent"]
    if parent is None:
        parent_text = "null"
    else:
        parent_text = f'{parent["git_commit"]} / {parent["activation_comment"]}'
    sources = ", ".join(state["sources"]) if state["sources"] else "none"
    delta_parts = []
    for status in ("active", "transformed", "resolved", "dormant"):
        values = ",".join(state["ledger_delta"][status]) or "none"
        delta_parts.append(f"{status.upper()}={values}")
    delta = "; ".join(delta_parts)
    return (
        f'CANON {state["state_id"]}\n'
        f"GIT: {git_commit}\n"
        f"PARENT: {parent_text}\n"
        f'RULES: {state["rules_path"]}\n'
        f'BIBLE: {state["bible_path"]}\n'
        f'MODE: {state["settlement_kind"]}\n'
        f'LICENSE: {state["content_license"]}\n'
        "WINDOWS: moves 18h; guest editor next 4h; settlement by +24h from this comment's server timestamp\n"
        f'WORLD {state["world_word_count"]}/120:\n'
        f'{state["world"]}\n'
        f'PRESSURE: {state["pressure"]}\n'
        f"SOURCES: {sources}\n"
        f"DELTA: {delta}\n"
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate schema and all states")
    validate_parser.add_argument("--root", type=Path, default=Path.cwd())

    render_parser = subparsers.add_parser("render-canon", help="render exact CANON bytes")
    render_parser.add_argument("--root", type=Path, default=Path.cwd())
    render_parser.add_argument("--state", type=Path, required=True)
    render_parser.add_argument("--git-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        repo_root = args.root.resolve()
        if args.command == "validate":
            states = validate_repository(repo_root)
            print(f"validated {len(states)} state(s)")
        else:
            state_path = args.state if args.state.is_absolute() else repo_root / args.state
            state = load_and_validate(state_path, repo_root)
            sys.stdout.write(render_canon(state, args.git_commit))
    except ValidationError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
