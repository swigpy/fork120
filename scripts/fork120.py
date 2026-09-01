#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed FORK/120 state validation and CANON rendering."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


V1_TOP_LEVEL_KEYS = {
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
V2_TOP_LEVEL_KEYS = V1_TOP_LEVEL_KEYS | {"round_title", "contributors"}
PARENT_V1_KEYS = {"state_id", "git_commit", "activation_comment"}
PARENT_V2_KEYS = {"state_id", "git_commit", "activation"}
CONTRIBUTOR_KEYS = {"handle", "move_id", "incorporated"}
LEDGER_KEYS = {"active", "transformed", "resolved", "dormant"}
STATE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-r[0-9]{3}$")
CHAPTER_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LEDGER_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
COMMENT_RE = re.compile(r"^c[1-9][0-9]*$")
ACTIVATION_RE = re.compile(r"^(?:comment:c[1-9][0-9]*|post:[1-9][0-9]*)$")
HANDLE_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PROPOSAL_RE = re.compile(r"^active-[0-9]{8}-[0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")
ACTIVATION_KEYS = {
    "version",
    "kind",
    "state_id",
    "state_commit",
    "post_id",
    "activation_comment",
    "activation_author",
    "activation_created_at",
    "relay_proposal_id",
    "relay_pull_request",
    "relay_merge_commit",
    "transport_normalization",
    "legacy_rendered_bytes",
    "legacy_rendered_sha256",
    "public_bytes",
    "public_sha256",
    "public_body",
}
GENESIS_REPAIR_KIND = "GENESIS_TERMINAL_LF_REPAIR"
GENESIS_REPAIR_PAIR = (
    "chapter-zero-r000",
    "861d5d744629bfe8e7f8a6a35ac4e9e2ed666ef1",
    3388,
    "c35281",
)
TRANSPORT_NORMALIZATION = "remove-exactly-one-terminal-lf"


class ValidationError(ValueError):
    """Raised when candidate state is not canonicalizable."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def word_count(text: str) -> int:
    """Count non-empty whitespace-delimited runs, as defined by the game rules."""

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
    """Validate one closed state and invariants not expressible in JSON Schema."""

    _require(isinstance(state, dict), "state must be an object")
    version = state.get("version")
    _require(type(version) is int and version in {1, 2}, "version must equal integer 1 or 2")
    expected_keys = V1_TOP_LEVEL_KEYS if version == 1 else V2_TOP_LEVEL_KEYS
    keys = set(state)
    _require(keys == expected_keys, f"closed state keys differ: {sorted(keys ^ expected_keys)}")

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
        _require(version == 1, "round zero remains the immutable v1 Genesis state")
        _require(kind == "GENESIS", "round zero must be GENESIS")
        _require(parent is None, "GENESIS parent must be null")
    else:
        _require(kind != "GENESIS", "GENESIS is only valid at round zero")
        parent_keys = PARENT_V1_KEYS if version == 1 else PARENT_V2_KEYS
        _require(isinstance(parent, dict) and set(parent) == parent_keys, "non-genesis parent must be closed")
        _require(isinstance(parent["state_id"], str) and STATE_ID_RE.fullmatch(parent["state_id"]) is not None, "invalid parent state_id")
        _require(isinstance(parent["git_commit"], str) and COMMIT_RE.fullmatch(parent["git_commit"]) is not None, "invalid parent git_commit")
        if version == 1:
            _require(isinstance(parent["activation_comment"], str) and COMMENT_RE.fullmatch(parent["activation_comment"]) is not None, "invalid parent activation_comment")
        else:
            _require(isinstance(parent["activation"], str) and ACTIVATION_RE.fullmatch(parent["activation"]) is not None, "invalid parent activation")

    if version == 2:
        round_title = state["round_title"]
        _require(isinstance(round_title, str) and round_title == round_title.strip(), "round_title must be trimmed")
        _require(1 <= len(round_title) <= 200, "round_title must contain 1 to 200 characters")
        expected_prefix = f"FORK/120: Chapter Zero — R{round_number:03d} — "
        _require(round_title.startswith(expected_prefix) and len(round_title) > len(expected_prefix), "round_title must identify Chapter Zero and the exact round")

        contributors = state["contributors"]
        _require(isinstance(contributors, list), "contributors must be an array")
        move_ids: list[str] = []
        handles: list[str] = []
        incorporated: list[str] = []
        for contributor in contributors:
            _require(isinstance(contributor, dict) and set(contributor) == CONTRIBUTOR_KEYS, "contributor must be closed")
            handle = contributor["handle"]
            move_id = contributor["move_id"]
            _require(isinstance(handle, str) and HANDLE_RE.fullmatch(handle) is not None, "invalid contributor handle")
            _require(isinstance(move_id, str) and COMMENT_RE.fullmatch(move_id) is not None, "invalid contributor move_id")
            _require(type(contributor["incorporated"]) is bool, "contributor incorporated must be boolean")
            handles.append(handle)
            move_ids.append(move_id)
            if contributor["incorporated"]:
                incorporated.append(move_id)
        _require(len(handles) == len(set(handles)), "contributor handles must be unique")
        _require(len(move_ids) == len(set(move_ids)), "contributor move ids must be unique")
        _require(move_ids == sorted(move_ids, key=lambda value: int(value[1:])), "contributors must be ordered by move id")

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
    if version == 2:
        _require(set(sources) == set(incorporated), "sources must equal incorporated contributor move ids")

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


def _sha256_utf8(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_activation_receipt(
    receipt: Any,
    repo_root: Path,
    receipt_path: Path | None = None,
) -> None:
    """Validate the single fail-closed Chapter Zero launch repair receipt."""

    _require(isinstance(receipt, dict), "activation receipt must be an object")
    keys = set(receipt)
    _require(
        keys == ACTIVATION_KEYS,
        f"closed activation receipt keys differ: {sorted(keys ^ ACTIVATION_KEYS)}",
    )
    _require(type(receipt["version"]) is int and receipt["version"] == 1, "activation receipt version must equal integer 1")
    _require(receipt["kind"] == GENESIS_REPAIR_KIND, "invalid activation receipt kind")

    state_id = receipt["state_id"]
    state_commit = receipt["state_commit"]
    post_id = receipt["post_id"]
    activation_comment = receipt["activation_comment"]
    pair = (state_id, state_commit, post_id, activation_comment)
    _require(pair == GENESIS_REPAIR_PAIR, "v1 activation repair is restricted to the recorded Genesis pair")
    if receipt_path is not None:
        _require(receipt_path.stem == state_id, "activation receipt filename must equal state_id")

    _require(COMMIT_RE.fullmatch(receipt["relay_merge_commit"]) is not None, "invalid relay merge commit")
    _require(receipt["activation_author"] == "bounded-curiosity", "invalid activation author")
    _validate_timestamp(receipt["activation_created_at"])
    _require(
        isinstance(receipt["relay_proposal_id"], str)
        and PROPOSAL_RE.fullmatch(receipt["relay_proposal_id"]) is not None,
        "invalid relay proposal id",
    )
    _require(
        type(receipt["relay_pull_request"]) is int and receipt["relay_pull_request"] > 0,
        "relay pull request must be a positive integer",
    )
    _require(
        receipt["transport_normalization"] == TRANSPORT_NORMALIZATION,
        "invalid transport normalization",
    )

    state_path = repo_root / "canon" / "states" / f"{state_id}.json"
    state = load_and_validate(state_path, repo_root)
    public_body = receipt["public_body"]
    _require(isinstance(public_body, str) and public_body != "", "public_body must be a non-empty string")
    _require(not public_body.endswith(("\n", "\r")), "public_body may not end in a line terminator")

    normalized_render = render_canon(state, state_commit)
    _require(public_body == normalized_render, "public_body differs from normalized renderer output")
    legacy_render = public_body + "\n"

    public_bytes = public_body.encode("utf-8")
    legacy_bytes = legacy_render.encode("utf-8")
    _require(
        type(receipt["public_bytes"]) is int and receipt["public_bytes"] == len(public_bytes),
        "public byte count mismatch",
    )
    _require(
        type(receipt["legacy_rendered_bytes"]) is int
        and receipt["legacy_rendered_bytes"] == len(legacy_bytes),
        "legacy rendered byte count mismatch",
    )
    _require(
        receipt["legacy_rendered_bytes"] == receipt["public_bytes"] + 1,
        "repair must remove exactly one byte",
    )
    _require(
        isinstance(receipt["public_sha256"], str)
        and SHA256_RE.fullmatch(receipt["public_sha256"]) is not None
        and receipt["public_sha256"] == _sha256_utf8(public_body),
        "public SHA-256 mismatch",
    )
    _require(
        isinstance(receipt["legacy_rendered_sha256"], str)
        and SHA256_RE.fullmatch(receipt["legacy_rendered_sha256"]) is not None
        and receipt["legacy_rendered_sha256"] == _sha256_utf8(legacy_render),
        "legacy rendered SHA-256 mismatch",
    )


def load_activation_receipt(path: Path, repo_root: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse {path}: {exc}") from exc
    validate_activation_receipt(receipt, repo_root, path)
    return receipt


def validate_activation_schema(repo_root: Path) -> None:
    schema_path = repo_root / "canon" / "activation.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse activation schema: {exc}") from exc
    _require(schema.get("additionalProperties") is False, "activation schema root must be closed")
    _require(
        set(schema.get("required", [])) == ACTIVATION_KEYS,
        "activation schema required keys differ from validator",
    )
    _require(
        set(schema.get("properties", {})) == ACTIVATION_KEYS,
        "activation schema properties differ from validator",
    )


def validate_schema(repo_root: Path) -> None:
    schema_path = repo_root / "canon" / "state.schema.json"
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse schema: {exc}") from exc
    _require(schema.get("additionalProperties") is False, "schema root must be closed")
    _require(set(schema.get("properties", {})) == V2_TOP_LEVEL_KEYS, "schema properties differ from validator")
    _require(set(schema.get("required", [])) == V1_TOP_LEVEL_KEYS, "schema common required keys differ from validator")


def discover_states(repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in (repo_root / "canon" / "examples", repo_root / "canon" / "states"):
        if directory.is_dir():
            paths.extend(sorted(directory.glob("*.json")))
    return paths


def discover_activation_receipts(repo_root: Path) -> list[Path]:
    directory = repo_root / "canon" / "activations"
    return sorted(directory.glob("*.json")) if directory.is_dir() else []


def validate_repository(repo_root: Path) -> tuple[list[Path], list[Path]]:
    validate_schema(repo_root)
    validate_activation_schema(repo_root)
    states = discover_states(repo_root)
    _require(states != [], "repository contains no candidate states")
    for path in states:
        load_and_validate(path, repo_root)

    receipts = discover_activation_receipts(repo_root)
    _require(receipts != [], "repository contains no activation receipt")
    for path in receipts:
        load_activation_receipt(path, repo_root)
    return states, receipts


def render_canon(state: dict[str, Any], git_commit: str) -> str:
    _require(COMMIT_RE.fullmatch(git_commit) is not None, "git commit must be 40 lowercase hex characters")
    parent = state["parent"]
    if parent is None:
        parent_text = "null"
    elif state["version"] == 1:
        parent_text = f'{parent["git_commit"]} / {parent["activation_comment"]}'
    else:
        parent_text = f'{parent["git_commit"]} / {parent["activation"]}'
    sources = ", ".join(state["sources"]) if state["sources"] else "none"
    delta_parts = []
    for status in ("active", "transformed", "resolved", "dormant"):
        values = ",".join(state["ledger_delta"][status]) or "none"
        delta_parts.append(f"{status.upper()}={values}")
    delta = "; ".join(delta_parts)
    window_origin = "comment" if state["version"] == 1 else "post"
    attribution = ""
    if state["version"] == 2:
        contributors = ", ".join(
            f'{item["handle"]} ({item["move_id"]})' for item in state["contributors"]
        ) or "none"
        incorporated = ", ".join(
            f'{item["handle"]} ({item["move_id"]})'
            for item in state["contributors"]
            if item["incorporated"]
        ) or "none"
        attribution = f"CONTRIBUTORS: {contributors}\nINCORPORATED: {incorporated}\n"
    return (
        f'CANON {state["state_id"]}\n'
        f"GIT: {git_commit}\n"
        f"PARENT: {parent_text}\n"
        f'RULES: {state["rules_path"]}\n'
        f'BIBLE: {state["bible_path"]}\n'
        f'MODE: {state["settlement_kind"]}\n'
        f'LICENSE: {state["content_license"]}\n'
        f"WINDOWS: moves 18h; guest editor next 4h; settlement by +24h from this {window_origin}'s server timestamp\n"
        f'WORLD {state["world_word_count"]}/120:\n'
        f'{state["world"]}\n'
        f'PRESSURE: {state["pressure"]}\n'
        f"{attribution}"
        f"SOURCES: {sources}\n"
        f"DELTA: {delta}"
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
    round_parser = subparsers.add_parser("render-round-post", help="render exact v2 post title and body as JSON")
    round_parser.add_argument("--root", type=Path, default=Path.cwd())
    round_parser.add_argument("--state", type=Path, required=True)
    round_parser.add_argument("--git-commit", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        repo_root = args.root.resolve()
        if args.command == "validate":
            states, receipts = validate_repository(repo_root)
            print(f"validated {len(states)} state(s) and {len(receipts)} activation receipt(s)")
        else:
            state_path = args.state if args.state.is_absolute() else repo_root / args.state
            state = load_and_validate(state_path, repo_root)
            if args.command == "render-round-post":
                _require(state["version"] == 2 and state["round"] >= 1, "round posts require a non-Genesis v2 state")
                sys.stdout.write(json.dumps({"title": state["round_title"], "body": render_canon(state, args.git_commit)}, ensure_ascii=False, separators=(",", ":")))
            else:
                sys.stdout.write(render_canon(state, args.git_commit))
    except ValidationError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
