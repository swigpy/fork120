#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Fail-closed FORK/120 state validation and deterministic rendering."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any


COMMON_STATE_KEYS = {
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
    "content_license",
    "created_at",
}
V1_TOP_LEVEL_KEYS = COMMON_STATE_KEYS | {"ledger_delta"}
V2_TOP_LEVEL_KEYS = V1_TOP_LEVEL_KEYS | {"round_title", "contributors"}
V3_TOP_LEVEL_KEYS = COMMON_STATE_KEYS | {
    "mechanics_path",
    "round_title",
    "chapter_status",
    "chapter_outcome",
    "contributors",
    "editor_proposals",
    "continuity_challenges",
    "ineligible_moves",
    "selection",
    "clocks",
    "clock_changes",
    "applied_pressure",
    "pressure_effect",
    "ledger_state",
    "ledger_changes",
    "stasis_reason",
}
ALL_STATE_KEYS = V1_TOP_LEVEL_KEYS | V2_TOP_LEVEL_KEYS | V3_TOP_LEVEL_KEYS

PARENT_V1_KEYS = {"state_id", "git_commit", "activation_comment"}
PARENT_V2_KEYS = {"state_id", "git_commit", "activation"}
CONTRIBUTOR_KEYS = {"handle", "move_id", "incorporated"}
EDITOR_KEYS = {"handle", "comment_id", "used"}
CHALLENGE_KEYS = {"handle", "comment_id", "disposition", "note"}
INELIGIBLE_KEYS = {"handle", "comment_id", "disposition", "note"}
SELECTION_KEYS = {"spine", "carries", "hook", "rationale", "exclusions"}
EXCLUSION_KEYS = {"move_id", "reason"}
CLOCK_KEYS = {"id", "label", "value", "maximum", "completion"}
CLOCK_CHANGE_KEYS = {"id", "from", "to", "source", "reason"}
PRESSURE_EFFECT_KEYS = {"kind", "target", "to"}
LEDGER_KEYS = {"active", "transformed", "resolved", "dormant"}
LEDGER_CHANGE_KEYS = {"id", "from", "to", "source", "reason"}
LEDGER_STATUSES = ("ACTIVE", "TRANSFORMED", "RESOLVED", "DORMANT")
INELIGIBLE_DISPOSITIONS = {
    "LATE",
    "WRONG_BASE",
    "MALFORMED",
    "UNLICENSED",
    "UNSAFE",
    "DUPLICATE_CITIZEN",
    "RULE_VIOLATION",
}
STATUS_TO_KEY = {status: status.lower() for status in LEDGER_STATUSES}

MECHANICS_KEYS = {
    "version",
    "chapter_id",
    "migration_parent",
    "playable_rounds",
    "stasis_limit",
    "clocks",
    "ledger_baseline",
}
MIGRATION_PARENT_KEYS = {"state_id", "state_commit", "activation"}
PLAYABLE_ROUNDS_KEYS = {"first", "last", "terminal_state_round"}
MECHANICS_CLOCK_KEYS = {
    "id",
    "label",
    "initial_value",
    "maximum",
    "completion_ledger_id",
    "completion_status",
    "requires_new_active_consequence",
    "completion_consequence",
}

GENESIS_ACTIVATION_KEYS = {
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
ROUND_ACTIVATION_KEYS = {
    "version",
    "kind",
    "state_id",
    "state_commit",
    "post_id",
    "activation_author",
    "activation_created_at",
    "relay_proposal_id",
    "relay_pull_request",
    "relay_merge_commit",
    "public_title_bytes",
    "public_title_sha256",
    "public_body_bytes",
    "public_body_sha256",
    "public_title",
    "public_body",
}

STATE_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*-r[0-9]{3}$")
CHAPTER_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
LEDGER_ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
COMMENT_RE = re.compile(r"^c[1-9][0-9]*$")
ACTIVATION_RE = re.compile(r"^(?:comment:c[1-9][0-9]*|post:[1-9][0-9]*)$")
HANDLE_RE = re.compile(r"^[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PROPOSAL_RE = re.compile(r"^active-[0-9]{8}-[0-9]{4}-[a-z0-9]+(?:-[a-z0-9]+)*$")
LEGACY_CLOCK_RE = re.compile(r"\b(?:Whale|Wells|Bell)\s+[0-9]+/[0-9]+\b")

GENESIS_REPAIR_KIND = "GENESIS_TERMINAL_LF_REPAIR"
ROUND_POST_KIND = "ROUND_POST"
GENESIS_REPAIR_PAIR = (
    "chapter-zero-r000",
    "861d5d744629bfe8e7f8a6a35ac4e9e2ed666ef1",
    3388,
    "c35281",
)
TRANSPORT_NORMALIZATION = "remove-exactly-one-terminal-lf"

IMMUTABLE_PATTERNS = (
    "canon/states/*.json",
    "canon/activations/*.json",
    "rules/game-v*.md",
    "rules/canonicalization-v*.md",
    "world/bible-v*.md",
    "world/*mechanics-v*.json",
    "world/regions/**",
    "ops/bounded-curiosity-chronicler-v*.md",
)


class ValidationError(ValueError):
    """Raised when candidate state is not canonicalizable."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def word_count(text: str) -> int:
    """Count non-empty whitespace-delimited runs, as defined by the game rules."""

    return len(re.findall(r"\S+", text))


def _validate_line(value: Any, field: str, maximum: int = 1000) -> None:
    _require(isinstance(value, str), f"{field} must be a string")
    _require(value != "" and value == value.strip(), f"{field} must be trimmed and non-empty")
    _require("\n" not in value and "\r" not in value, f"{field} must occupy one line")
    _require(len(value) <= maximum, f"{field} is too long")


def _parse_timestamp(value: Any, field: str = "created_at") -> datetime:
    _require(isinstance(value, str), f"{field} must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError(f"{field} must be ISO-8601") from exc
    _require(parsed.tzinfo is not None, f"{field} must include a timezone")
    return parsed


def _validate_timestamp(value: Any, field: str = "created_at") -> None:
    _parse_timestamp(value, field)


def _validate_pinned_path(
    repo_root: Path,
    value: Any,
    prefix: str,
    suffix: str,
    field: str,
) -> Path:
    _require(isinstance(value, str), f"{field} must be a string")
    path = PurePosixPath(value)
    _require(not path.is_absolute(), f"{field} must be repository-relative")
    _require(".." not in path.parts and "." not in path.parts, f"{field} may not traverse")
    _require(value.startswith(prefix + "/") and value.endswith(suffix), f"{field} has invalid scope")
    resolved = repo_root.joinpath(*path.parts)
    _require(resolved.is_file(), f"{field} does not exist: {value}")
    return resolved


def _validate_ledger_state(value: Any, field: str, active_cap: bool = True) -> dict[str, str]:
    _require(isinstance(value, dict) and set(value) == LEDGER_KEYS, f"{field} must be closed")
    all_ids: list[str] = []
    status_by_id: dict[str, str] = {}
    for status in LEDGER_STATUSES:
        key = STATUS_TO_KEY[status]
        values = value[key]
        _require(isinstance(values, list), f"{field}.{key} must be an array")
        _require(
            all(isinstance(item, str) and LEDGER_ID_RE.fullmatch(item) is not None for item in values),
            f"invalid ledger id in {field}.{key}",
        )
        _require(len(values) == len(set(values)), f"duplicate ledger id within {field}.{key}")
        if active_cap and status == "ACTIVE":
            _require(len(values) <= 12, f"{field}.active may contain at most twelve ids")
        for item in values:
            status_by_id[item] = status
        all_ids.extend(values)
    _require(len(all_ids) == len(set(all_ids)), f"ledger ids in {field} may occur in only one status")
    return status_by_id


def _transition_allowed(old: str | None, new: str) -> bool:
    if old is None:
        return new == "ACTIVE"
    if old == new:
        return True
    if old == "ACTIVE":
        return new in {"TRANSFORMED", "RESOLVED", "DORMANT"}
    if old == "DORMANT":
        return new == "ACTIVE"
    return False


def validate_mechanics(mechanics: Any, mechanics_path: Path | None = None) -> None:
    _require(isinstance(mechanics, dict), "mechanics must be an object")
    _require(set(mechanics) == MECHANICS_KEYS, "mechanics keys differ from the closed contract")
    _require(type(mechanics["version"]) is int and mechanics["version"] == 1, "mechanics version must equal 1")
    chapter_id = mechanics["chapter_id"]
    _require(isinstance(chapter_id, str) and CHAPTER_ID_RE.fullmatch(chapter_id) is not None, "invalid mechanics chapter_id")

    migration = mechanics["migration_parent"]
    _require(isinstance(migration, dict) and set(migration) == MIGRATION_PARENT_KEYS, "migration_parent must be closed")
    _require(isinstance(migration["state_id"], str) and STATE_ID_RE.fullmatch(migration["state_id"]) is not None, "invalid migration state_id")
    _require(isinstance(migration["state_commit"], str) and COMMIT_RE.fullmatch(migration["state_commit"]) is not None, "invalid migration state_commit")
    _require(isinstance(migration["activation"], str) and migration["activation"].startswith("post:") and ACTIVATION_RE.fullmatch(migration["activation"]) is not None, "invalid migration activation")

    rounds = mechanics["playable_rounds"]
    _require(isinstance(rounds, dict) and set(rounds) == PLAYABLE_ROUNDS_KEYS, "playable_rounds must be closed")
    _require(all(type(rounds[key]) is int and rounds[key] >= 0 for key in PLAYABLE_ROUNDS_KEYS), "playable round values must be non-negative integers")
    _require(rounds["first"] <= rounds["last"], "playable round range is inverted")
    _require(rounds["terminal_state_round"] == rounds["last"] + 1, "terminal state must immediately follow the last playable round")
    _require(type(mechanics["stasis_limit"]) is int and mechanics["stasis_limit"] >= 0, "stasis_limit must be a non-negative integer")

    clocks = mechanics["clocks"]
    _require(isinstance(clocks, list) and clocks, "mechanics clocks must be a non-empty array")
    clock_ids: list[str] = []
    completion_ids: list[str] = []
    for clock in clocks:
        _require(isinstance(clock, dict) and set(clock) == MECHANICS_CLOCK_KEYS, "mechanics clock must be closed")
        clock_id = clock["id"]
        ledger_id = clock["completion_ledger_id"]
        _require(isinstance(clock_id, str) and LEDGER_ID_RE.fullmatch(clock_id) is not None, "invalid mechanics clock id")
        _validate_line(clock["label"], "mechanics clock label", 100)
        _require(type(clock["initial_value"]) is int and clock["initial_value"] >= 0, "invalid initial clock value")
        _require(type(clock["maximum"]) is int and clock["maximum"] >= 1, "invalid clock maximum")
        _require(clock["initial_value"] <= clock["maximum"], "initial clock value exceeds maximum")
        _require(isinstance(ledger_id, str) and LEDGER_ID_RE.fullmatch(ledger_id) is not None, "invalid completion ledger id")
        _require(
            clock["completion_status"] in {"TRANSFORMED", "RESOLVED"},
            "clock completion status must be TRANSFORMED or RESOLVED",
        )
        _require(type(clock["requires_new_active_consequence"]) is bool, "completion consequence flag must be boolean")
        _validate_line(clock["completion_consequence"], "completion consequence", 1000)
        clock_ids.append(clock_id)
        completion_ids.append(ledger_id)
    _require(len(clock_ids) == len(set(clock_ids)), "mechanics clock ids must be unique")
    _require(len(completion_ids) == len(set(completion_ids)), "clock completion ledger ids must be unique")

    baseline = _validate_ledger_state(mechanics["ledger_baseline"], "ledger_baseline")
    for ledger_id in completion_ids:
        _require(baseline.get(ledger_id) == "ACTIVE", f"clock ledger id {ledger_id} must begin ACTIVE")
    if mechanics_path is not None:
        _require(mechanics_path.name.endswith("mechanics-v0.3.json"), "v3 mechanics must use a versioned v0.3 filename")


def load_mechanics(path: Path) -> dict[str, Any]:
    try:
        mechanics = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse {path}: {exc}") from exc
    validate_mechanics(mechanics, path)
    return mechanics


def _validate_parent(state: dict[str, Any], version: int, round_number: int, kind: str) -> None:
    parent = state["parent"]
    if round_number == 0:
        _require(version == 1, "round zero remains the immutable v1 Genesis state")
        _require(kind == "GENESIS", "round zero must be GENESIS")
        _require(parent is None, "GENESIS parent must be null")
        return
    _require(kind != "GENESIS", "GENESIS is only valid at round zero")
    parent_keys = PARENT_V1_KEYS if version == 1 else PARENT_V2_KEYS
    _require(isinstance(parent, dict) and set(parent) == parent_keys, "non-genesis parent must be closed")
    _require(isinstance(parent["state_id"], str) and STATE_ID_RE.fullmatch(parent["state_id"]) is not None, "invalid parent state_id")
    _require(isinstance(parent["git_commit"], str) and COMMIT_RE.fullmatch(parent["git_commit"]) is not None, "invalid parent git_commit")
    if version == 1:
        _require(isinstance(parent["activation_comment"], str) and COMMENT_RE.fullmatch(parent["activation_comment"]) is not None, "invalid parent activation_comment")
    else:
        _require(isinstance(parent["activation"], str) and ACTIVATION_RE.fullmatch(parent["activation"]) is not None, "invalid parent activation")


def _validate_contributors(state: dict[str, Any]) -> tuple[list[str], list[str]]:
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
    return move_ids, incorporated


def _validate_v3_adjudication(state: dict[str, Any], move_ids: list[str], incorporated: list[str]) -> None:
    _require(
        all(contributor["handle"] != "bounded-curiosity" for contributor in state["contributors"]),
        "the Chronicler may not be a v3 contributor",
    )
    editor_ids: list[str] = []
    editor_handles: list[str] = []
    used_editors = 0
    _require(isinstance(state["editor_proposals"], list), "editor_proposals must be an array")
    for proposal in state["editor_proposals"]:
        _require(isinstance(proposal, dict) and set(proposal) == EDITOR_KEYS, "editor proposal must be closed")
        _require(isinstance(proposal["handle"], str) and HANDLE_RE.fullmatch(proposal["handle"]) is not None, "invalid editor handle")
        _require(proposal["handle"] != "bounded-curiosity", "the Chronicler may not be a guest editor")
        _require(isinstance(proposal["comment_id"], str) and COMMENT_RE.fullmatch(proposal["comment_id"]) is not None, "invalid editor comment id")
        _require(type(proposal["used"]) is bool, "editor used must be boolean")
        editor_ids.append(proposal["comment_id"])
        editor_handles.append(proposal["handle"])
        used_editors += int(proposal["used"])
    _require(len(editor_ids) == len(set(editor_ids)), "editor comment ids must be unique")
    _require(len(editor_handles) == len(set(editor_handles)), "editor handles must be unique")
    _require(editor_ids == sorted(editor_ids, key=lambda value: int(value[1:])), "editor proposals must be ordered by comment id")
    _require(used_editors <= 1, "at most one editor proposal may be used")

    challenge_ids: list[str] = []
    _require(isinstance(state["continuity_challenges"], list), "continuity_challenges must be an array")
    for challenge in state["continuity_challenges"]:
        _require(isinstance(challenge, dict) and set(challenge) == CHALLENGE_KEYS, "continuity challenge must be closed")
        _require(isinstance(challenge["handle"], str) and HANDLE_RE.fullmatch(challenge["handle"]) is not None, "invalid challenge handle")
        _require(isinstance(challenge["comment_id"], str) and COMMENT_RE.fullmatch(challenge["comment_id"]) is not None, "invalid challenge comment id")
        _require(challenge["disposition"] in {"REPAIRED", "PRESERVED_UNCERTAINTY", "FORKED", "REJECTED"}, "invalid challenge disposition")
        _validate_line(challenge["note"], "challenge note", 500)
        challenge_ids.append(challenge["comment_id"])
    _require(len(challenge_ids) == len(set(challenge_ids)), "challenge comment ids must be unique")
    _require(challenge_ids == sorted(challenge_ids, key=lambda value: int(value[1:])), "continuity challenges must be ordered by comment id")

    ineligible_ids: list[str] = []
    _require(isinstance(state["ineligible_moves"], list), "ineligible_moves must be an array")
    for move in state["ineligible_moves"]:
        _require(isinstance(move, dict) and set(move) == INELIGIBLE_KEYS, "ineligible move must be closed")
        _require(isinstance(move["handle"], str) and HANDLE_RE.fullmatch(move["handle"]) is not None, "invalid ineligible move handle")
        _require(isinstance(move["comment_id"], str) and COMMENT_RE.fullmatch(move["comment_id"]) is not None, "invalid ineligible move comment id")
        _require(move["disposition"] in INELIGIBLE_DISPOSITIONS, "invalid ineligible move disposition")
        _validate_line(move["note"], "ineligible move note", 500)
        ineligible_ids.append(move["comment_id"])
    _require(len(ineligible_ids) == len(set(ineligible_ids)), "ineligible move comment ids must be unique")
    _require(ineligible_ids == sorted(ineligible_ids, key=lambda value: int(value[1:])), "ineligible moves must be ordered by comment id")
    _require(set(ineligible_ids).isdisjoint(move_ids), "a comment cannot be both a contributor and ineligible")

    kind = state["settlement_kind"]
    selection = state["selection"]
    if kind == "PRESSURE":
        _require(move_ids == [], "PRESSURE settlement may not list contributors")
        _require(selection is None, "PRESSURE settlement may not contain a selection")
        return

    _require(move_ids != [], "MOVES settlement requires at least one valid contributor")
    _require(isinstance(selection, dict) and set(selection) == SELECTION_KEYS, "MOVES selection must be closed")
    _require(isinstance(selection["spine"], str) and COMMENT_RE.fullmatch(selection["spine"]) is not None, "invalid selection spine")
    _require(isinstance(selection["hook"], str) and COMMENT_RE.fullmatch(selection["hook"]) is not None, "invalid selection hook")
    carries = selection["carries"]
    _require(isinstance(carries, list) and len(carries) <= 2, "selection carries must contain at most two ids")
    _require(all(isinstance(item, str) and COMMENT_RE.fullmatch(item) is not None for item in carries), "invalid carry source")
    _require(len(carries) == len(set(carries)), "carry sources must be unique")
    _validate_line(selection["rationale"], "selection rationale", 1000)

    role_ids = {selection["spine"], selection["hook"], *carries}
    _require(role_ids == set(incorporated), "composition roles must cover exactly the incorporated sources")

    exclusions = selection["exclusions"]
    _require(isinstance(exclusions, list), "selection exclusions must be an array")
    excluded_ids: list[str] = []
    for exclusion in exclusions:
        _require(isinstance(exclusion, dict) and set(exclusion) == EXCLUSION_KEYS, "selection exclusion must be closed")
        _require(isinstance(exclusion["move_id"], str) and COMMENT_RE.fullmatch(exclusion["move_id"]) is not None, "invalid excluded move id")
        _validate_line(exclusion["reason"], "exclusion reason", 500)
        excluded_ids.append(exclusion["move_id"])
    _require(len(excluded_ids) == len(set(excluded_ids)), "excluded move ids must be unique")
    _require(excluded_ids == sorted(excluded_ids, key=lambda value: int(value[1:])), "exclusions must be ordered by move id")
    expected_exclusions = [move_id for move_id in move_ids if move_id not in incorporated]
    _require(excluded_ids == expected_exclusions, "exclusions must record every non-incorporated valid move")


def _validate_v3_mechanics(state: dict[str, Any], mechanics: dict[str, Any]) -> None:
    kind = state["settlement_kind"]
    sources = state["sources"]
    spine = state["selection"]["spine"] if state["selection"] is not None else None
    terminal_round = mechanics["playable_rounds"]["terminal_state_round"]
    is_terminal = state["round"] == terminal_round

    clock_defs = mechanics["clocks"]
    clock_by_id = {clock["id"]: clock for clock in clock_defs}
    clocks = state["clocks"]
    _require(isinstance(clocks, list) and len(clocks) == len(clock_defs), "clocks must match the mechanics clock set")
    for actual, definition in zip(clocks, clock_defs):
        _require(isinstance(actual, dict) and set(actual) == CLOCK_KEYS, "clock must be closed")
        _require(actual["id"] == definition["id"], "clock order and ids must match mechanics")
        _require(actual["label"] == definition["label"], "clock label differs from mechanics")
        _require(type(actual["value"]) is int and 0 <= actual["value"] <= definition["maximum"], "clock value is outside its range")
        _require(type(actual["maximum"]) is int and actual["maximum"] == definition["maximum"], "clock maximum differs from mechanics")
        _require(actual["completion"] == definition["completion_consequence"], "clock completion text differs from mechanics")

    changes = state["clock_changes"]
    _require(isinstance(changes, list) and len(changes) <= 1, "at most one clock may change")
    for change in changes:
        _require(isinstance(change, dict) and set(change) == CLOCK_CHANGE_KEYS, "clock change must be closed")
        _require(change["id"] in clock_by_id, "clock change targets an unknown clock")
        _require(type(change["from"]) is int and type(change["to"]) is int, "clock endpoints must be integers")
        _require(change["to"] == change["from"] + 1, "clock change must advance exactly one step")
        _require(change["to"] <= clock_by_id[change["id"]]["maximum"], "clock change exceeds maximum")
        expected_source = spine if kind == "MOVES" else "PRESSURE"
        _require(change["source"] == expected_source, "clock change source must be the spine or PRESSURE")
        _validate_line(change["reason"], "clock change reason", 500)

    ledger_map = _validate_ledger_state(state["ledger_state"], "ledger_state")
    incomplete_clock_threads = {
        definition["completion_ledger_id"]
        for actual, definition in zip(clocks, clock_defs)
        if actual["value"] < actual["maximum"]
    }
    for actual, definition in zip(clocks, clock_defs):
        if actual["value"] == actual["maximum"]:
            expected_status = definition["completion_status"]
        elif is_terminal:
            expected_status = "DORMANT"
        else:
            expected_status = "ACTIVE"
        _require(
            ledger_map.get(definition["completion_ledger_id"]) == expected_status,
            f'clock thread {definition["completion_ledger_id"]} must be {expected_status}',
        )

    ledger_changes = state["ledger_changes"]
    _require(isinstance(ledger_changes, list), "ledger_changes must be an array")
    change_ids: list[str] = []
    mechanical_ledger_changes: list[dict[str, Any]] = []
    introduced: list[dict[str, Any]] = []
    for change in ledger_changes:
        _require(isinstance(change, dict) and set(change) == LEDGER_CHANGE_KEYS, "ledger change must be closed")
        ledger_id = change["id"]
        old = change["from"]
        new = change["to"]
        _require(isinstance(ledger_id, str) and LEDGER_ID_RE.fullmatch(ledger_id) is not None, "invalid ledger change id")
        _require(old is None or old in LEDGER_STATUSES, "invalid ledger change origin")
        _require(new in LEDGER_STATUSES, "invalid ledger change destination")
        _require(_transition_allowed(old, new), f"forbidden ledger transition for {ledger_id}: {old}->{new}")
        expected_sources = set(sources) if kind == "MOVES" else {"PRESSURE"}
        if is_terminal:
            expected_sources.add("CLOSURE")
        _require(change["source"] in expected_sources, "ledger change source must be incorporated, PRESSURE, or terminal CLOSURE")
        if old != new:
            expected_source = spine if kind == "MOVES" else "PRESSURE"
            if change["source"] == "CLOSURE":
                _require(old == "ACTIVE" and new == "DORMANT", "CLOSURE may only make an active thread dormant")
                _require(
                    ledger_id in incomplete_clock_threads,
                    "CLOSURE may only archive an incomplete clock thread",
                )
            else:
                _require(change["source"] == expected_source, "mechanical ledger change source must be the spine or PRESSURE")
            mechanical_ledger_changes.append(change)
        if old is None:
            introduced.append(change)
        _validate_line(change["reason"], "ledger change reason", 500)
        change_ids.append(ledger_id)
    _require(len(change_ids) == len(set(change_ids)), "ledger change ids must be unique")
    _require(len(introduced) <= 1, "a settlement may introduce at most one active ledger id")
    primary_mechanical_changes = [
        change for change in mechanical_ledger_changes if change["source"] != "CLOSURE"
    ]

    if changes:
        change = changes[0]
        definition = clock_by_id[change["id"]]
        completing = change["to"] == definition["maximum"]
        if completing:
            required = [
                item
                for item in primary_mechanical_changes
                if item["id"] == definition["completion_ledger_id"]
                and item["to"] == definition["completion_status"]
            ]
            _require(len(required) == 1, "clock completion must transition its linked ledger id")
            if definition["requires_new_active_consequence"]:
                _require(len(introduced) == 1, "clock completion must introduce one active consequence")
            allowed_ids = {definition["completion_ledger_id"]}
            if introduced:
                allowed_ids.add(introduced[0]["id"])
            _require(
                all(item["id"] in allowed_ids for item in primary_mechanical_changes),
                "clock completion contains an unrelated mechanical ledger change",
            )
        else:
            _require(primary_mechanical_changes == [], "a clock step may not carry an unrelated ledger transition")
    else:
        _require(len(primary_mechanical_changes) <= 1, "a settlement may contain at most one primary ledger transition")

    progress = bool(changes or mechanical_ledger_changes)
    if progress:
        _require(state["stasis_reason"] is None, "progress settlement must set stasis_reason to null")
    else:
        _validate_line(state["stasis_reason"], "stasis_reason", 500)

    effect = state["pressure_effect"]
    if state["chapter_status"] == "CLOSED":
        _require(effect is None, "closed chapter may not declare a pressure effect")
    else:
        _require(isinstance(effect, dict) and set(effect) == PRESSURE_EFFECT_KEYS, "active chapter pressure_effect must be closed")
        _require(effect["kind"] in {"CLOCK", "LEDGER"}, "invalid pressure effect kind")
        _require(isinstance(effect["target"], str) and LEDGER_ID_RE.fullmatch(effect["target"]) is not None, "invalid pressure target")
        if effect["kind"] == "CLOCK":
            _require(effect["to"] is None, "CLOCK pressure effect must set to to null")
            _require(effect["target"] in clock_by_id, "pressure targets an unknown clock")
            current = next(clock for clock in clocks if clock["id"] == effect["target"])
            _require(current["value"] < current["maximum"], "pressure may not target a complete clock")
        else:
            _require(effect["to"] in LEDGER_STATUSES, "LEDGER pressure effect requires a status destination")
            _require(
                effect["target"] not in {clock["completion_ledger_id"] for clock in clock_defs},
                "ledger pressure may not bypass a clock-owned thread",
            )
            current_status = ledger_map.get(effect["target"])
            _require(_transition_allowed(current_status, effect["to"]), "pressure declares a forbidden ledger transition")
            _require(current_status != effect["to"], "pressure effect must make mechanical progress")


def validate_state(state: Any, repo_root: Path, state_path: Path | None = None) -> None:
    """Validate one closed state and invariants not expressible in JSON Schema."""

    _require(isinstance(state, dict), "state must be an object")
    version = state.get("version")
    _require(type(version) is int and version in {1, 2, 3}, "version must equal integer 1, 2, or 3")
    expected_keys = {1: V1_TOP_LEVEL_KEYS, 2: V2_TOP_LEVEL_KEYS, 3: V3_TOP_LEVEL_KEYS}[version]
    keys = set(state)
    _require(keys == expected_keys, f"closed state keys differ: {sorted(keys ^ expected_keys)}")

    state_id = state["state_id"]
    _require(isinstance(state_id, str) and STATE_ID_RE.fullmatch(state_id) is not None, "invalid state_id")
    if state_path is not None:
        _require(state_path.stem == state_id, "state filename must equal state_id")

    rules_path = _validate_pinned_path(repo_root, state["rules_path"], "rules", ".md", "rules_path")
    _validate_pinned_path(repo_root, state["bible_path"], "world", ".md", "bible_path")
    mechanics: dict[str, Any] | None = None
    if version == 3:
        _require(state["rules_path"] == "rules/game-v0.3.md", "v3 state must pin rules/game-v0.3.md")
        _require(rules_path.name == "game-v0.3.md", "v3 rules filename is not canonical")
        mechanics_path = _validate_pinned_path(repo_root, state["mechanics_path"], "world", ".json", "mechanics_path")
        mechanics = load_mechanics(mechanics_path)

    chapter_id = state["chapter_id"]
    _require(isinstance(chapter_id, str) and CHAPTER_ID_RE.fullmatch(chapter_id) is not None, "invalid chapter_id")
    round_number = state["round"]
    _require(type(round_number) is int and round_number >= 0, "round must be a non-negative integer")
    if version == 3:
        _require(state_id == f"{chapter_id}-r{round_number:03d}", "state_id must encode chapter_id and round")
        _require(mechanics is not None and mechanics["chapter_id"] == chapter_id, "mechanics chapter differs from state")
    kind = state["settlement_kind"]
    _require(kind in {"GENESIS", "MOVES", "PRESSURE"}, "invalid settlement_kind")
    _validate_parent(state, version, round_number, kind)

    incorporated: list[str] = []
    move_ids: list[str] = []
    if version >= 2:
        _validate_line(state["round_title"], "round_title", 200)
        expected_prefix = f"FORK/120: Chapter Zero — R{round_number:03d} — "
        _require(state["round_title"].startswith(expected_prefix) and len(state["round_title"]) > len(expected_prefix), "round_title must identify Chapter Zero and the exact round")
        move_ids, incorporated = _validate_contributors(state)

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
    if version == 3:
        _validate_line(pressure, "pressure", 500)
        _require(LEGACY_CLOCK_RE.search(world) is None, "v3 WORLD may not duplicate structured clock counters")
        applied_pressure = state["applied_pressure"]
        if kind == "PRESSURE":
            _validate_line(applied_pressure, "applied_pressure", 500)
        else:
            _require(applied_pressure is None, "non-PRESSURE settlement must set applied_pressure to null")

    sources = state["sources"]
    _require(isinstance(sources, list), "sources must be an array")
    _require(all(isinstance(item, str) and COMMENT_RE.fullmatch(item) is not None for item in sources), "invalid source comment id")
    _require(len(sources) == len(set(sources)), "sources must be unique")
    if kind == "MOVES":
        _require(len(sources) >= 1, "MOVES settlement requires a source")
    else:
        _require(sources == [], f"{kind} settlement may not contain move sources")
    if version >= 2:
        _require(set(sources) == set(incorporated), "sources must equal incorporated contributor move ids")
    if version == 3:
        _require(sources == sorted(sources, key=lambda value: int(value[1:])), "sources must be ordered by comment id")

    if version < 3:
        ledger = state["ledger_delta"]
        _validate_ledger_state(ledger, "ledger_delta", active_cap=False)
        all_ids = sum((ledger[key] for key in ("active", "transformed", "resolved", "dormant")), [])
        _require(len(all_ids) <= 12, "active ledger delta may contain at most twelve ids")
    else:
        assert mechanics is not None
        status = state["chapter_status"]
        _require(status in {"ACTIVE", "CLOSED"}, "invalid chapter_status")
        rounds = mechanics["playable_rounds"]
        if status == "ACTIVE":
            _require(round_number <= rounds["last"], "active state is past the final playable round")
            _require(state["chapter_outcome"] is None, "active chapter must set chapter_outcome to null")
        else:
            _require(round_number == rounds["terminal_state_round"], "closed chapter must use the terminal state round")
            _validate_line(state["chapter_outcome"], "chapter_outcome", 500)
        _validate_v3_adjudication(state, move_ids, incorporated)
        _validate_v3_mechanics(state, mechanics)

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


def _validate_relay_fields(receipt: dict[str, Any]) -> None:
    _require(COMMIT_RE.fullmatch(receipt["relay_merge_commit"]) is not None, "invalid relay merge commit")
    _require(receipt["activation_author"] == "bounded-curiosity", "invalid activation author")
    _validate_timestamp(receipt["activation_created_at"], "activation_created_at")
    _require(isinstance(receipt["relay_proposal_id"], str) and PROPOSAL_RE.fullmatch(receipt["relay_proposal_id"]) is not None, "invalid relay proposal id")
    _require(type(receipt["relay_pull_request"]) is int and receipt["relay_pull_request"] > 0, "relay pull request must be a positive integer")


def _validate_genesis_activation_receipt(
    receipt: dict[str, Any],
    repo_root: Path,
    receipt_path: Path | None,
) -> None:
    _require(set(receipt) == GENESIS_ACTIVATION_KEYS, f"closed activation receipt keys differ: {sorted(set(receipt) ^ GENESIS_ACTIVATION_KEYS)}")
    _require(receipt["kind"] == GENESIS_REPAIR_KIND, "invalid activation receipt kind")
    pair = (receipt["state_id"], receipt["state_commit"], receipt["post_id"], receipt["activation_comment"])
    _require(pair == GENESIS_REPAIR_PAIR, "v1 activation repair is restricted to the recorded Genesis pair")
    if receipt_path is not None:
        _require(receipt_path.stem == receipt["state_id"], "activation receipt filename must equal state_id")
    _validate_relay_fields(receipt)
    _require(receipt["transport_normalization"] == TRANSPORT_NORMALIZATION, "invalid transport normalization")

    state = load_and_validate(repo_root / "canon" / "states" / f'{receipt["state_id"]}.json', repo_root)
    _require(
        _parse_timestamp(receipt["activation_created_at"], "activation_created_at")
        >= _parse_timestamp(state["created_at"]),
        "activation may not predate state creation",
    )
    public_body = receipt["public_body"]
    _require(isinstance(public_body, str) and public_body != "", "public_body must be a non-empty string")
    _require(not public_body.endswith(("\n", "\r")), "public_body may not end in a line terminator")
    normalized_render = render_canon(state, receipt["state_commit"])
    _require(public_body == normalized_render, "public_body differs from normalized renderer output")
    legacy_render = public_body + "\n"
    _require(type(receipt["public_bytes"]) is int and receipt["public_bytes"] == len(public_body.encode("utf-8")), "public byte count mismatch")
    _require(type(receipt["legacy_rendered_bytes"]) is int and receipt["legacy_rendered_bytes"] == len(legacy_render.encode("utf-8")), "legacy rendered byte count mismatch")
    _require(receipt["legacy_rendered_bytes"] == receipt["public_bytes"] + 1, "repair must remove exactly one byte")
    _require(isinstance(receipt["public_sha256"], str) and SHA256_RE.fullmatch(receipt["public_sha256"]) is not None and receipt["public_sha256"] == _sha256_utf8(public_body), "public SHA-256 mismatch")
    _require(isinstance(receipt["legacy_rendered_sha256"], str) and SHA256_RE.fullmatch(receipt["legacy_rendered_sha256"]) is not None and receipt["legacy_rendered_sha256"] == _sha256_utf8(legacy_render), "legacy rendered SHA-256 mismatch")


def _validate_round_activation_receipt(
    receipt: dict[str, Any],
    repo_root: Path,
    receipt_path: Path | None,
) -> None:
    _require(set(receipt) == ROUND_ACTIVATION_KEYS, f"closed round activation receipt keys differ: {sorted(set(receipt) ^ ROUND_ACTIVATION_KEYS)}")
    _require(receipt["kind"] == ROUND_POST_KIND, "invalid round activation receipt kind")
    state_id = receipt["state_id"]
    _require(isinstance(state_id, str) and STATE_ID_RE.fullmatch(state_id) is not None, "invalid activation state_id")
    _require(isinstance(receipt["state_commit"], str) and COMMIT_RE.fullmatch(receipt["state_commit"]) is not None, "invalid activation state_commit")
    _require(type(receipt["post_id"]) is int and receipt["post_id"] > 0, "activation post id must be positive")
    if receipt_path is not None:
        _require(receipt_path.stem == state_id, "activation receipt filename must equal state_id")
    _validate_relay_fields(receipt)

    state = load_and_validate(repo_root / "canon" / "states" / f"{state_id}.json", repo_root)
    _require(state["version"] in {2, 3} and state["round"] >= 1, "round receipt requires a non-Genesis v2 or v3 state")
    _require(
        _parse_timestamp(receipt["activation_created_at"], "activation_created_at")
        >= _parse_timestamp(state["created_at"]),
        "activation may not predate state creation",
    )
    rendered = render_round_post(state, receipt["state_commit"])
    for field in ("public_title", "public_body"):
        _require(isinstance(receipt[field], str) and receipt[field] != "", f"{field} must be non-empty")
        _require(not receipt[field].endswith(("\n", "\r")), f"{field} may not end in a line terminator")
        _require(receipt[field] == rendered[field.removeprefix("public_")], f"{field} differs from renderer output")
        bytes_field = f"{field}_bytes"
        digest_field = f"{field}_sha256"
        _require(type(receipt[bytes_field]) is int and receipt[bytes_field] == len(receipt[field].encode("utf-8")), f"{field} byte count mismatch")
        _require(isinstance(receipt[digest_field], str) and SHA256_RE.fullmatch(receipt[digest_field]) is not None and receipt[digest_field] == _sha256_utf8(receipt[field]), f"{field} SHA-256 mismatch")


def validate_activation_receipt(
    receipt: Any,
    repo_root: Path,
    receipt_path: Path | None = None,
) -> None:
    """Validate a Genesis repair or ordinary round-post activation receipt."""

    _require(isinstance(receipt, dict), "activation receipt must be an object")
    version = receipt.get("version")
    _require(type(version) is int and version in {1, 2}, "activation receipt version must equal integer 1 or 2")
    if version == 1:
        _validate_genesis_activation_receipt(receipt, repo_root, receipt_path)
    else:
        _validate_round_activation_receipt(receipt, repo_root, receipt_path)


def load_activation_receipt(path: Path, repo_root: Path) -> dict[str, Any]:
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse {path}: {exc}") from exc
    validate_activation_receipt(receipt, repo_root, path)
    return receipt


def _load_schema(repo_root: Path, relative: str) -> dict[str, Any]:
    try:
        return json.loads((repo_root / relative).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot parse {relative}: {exc}") from exc


def validate_schemas(repo_root: Path) -> None:
    state_schema = _load_schema(repo_root, "canon/state.schema.json")
    _require(state_schema.get("additionalProperties") is False, "state schema root must be closed")
    _require(set(state_schema.get("properties", {})) == ALL_STATE_KEYS, "state schema properties differ from validator")
    _require(set(state_schema.get("required", [])) == COMMON_STATE_KEYS, "state schema common required keys differ from validator")

    activation_schema = _load_schema(repo_root, "canon/activation.schema.json")
    _require(activation_schema.get("additionalProperties") is False, "activation schema root must be closed")
    _require(set(activation_schema.get("required", [])) == GENESIS_ACTIVATION_KEYS, "activation schema required keys differ from validator")
    _require(set(activation_schema.get("properties", {})) == GENESIS_ACTIVATION_KEYS, "activation schema properties differ from validator")

    round_schema = _load_schema(repo_root, "canon/round-activation.schema.json")
    _require(round_schema.get("additionalProperties") is False, "round activation schema root must be closed")
    _require(set(round_schema.get("required", [])) == ROUND_ACTIVATION_KEYS, "round activation schema required keys differ from validator")
    _require(set(round_schema.get("properties", {})) == ROUND_ACTIVATION_KEYS, "round activation schema properties differ from validator")

    mechanics_schema = _load_schema(repo_root, "canon/mechanics.schema.json")
    _require(mechanics_schema.get("additionalProperties") is False, "mechanics schema root must be closed")
    _require(set(mechanics_schema.get("required", [])) == MECHANICS_KEYS, "mechanics schema required keys differ from validator")
    _require(set(mechanics_schema.get("properties", {})) == MECHANICS_KEYS, "mechanics schema properties differ from validator")


def discover_states(repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory in (repo_root / "canon" / "examples", repo_root / "canon" / "states"):
        if directory.is_dir():
            paths.extend(sorted(directory.glob("*.json")))
    return paths


def discover_activation_receipts(repo_root: Path) -> list[Path]:
    directory = repo_root / "canon" / "activations"
    return sorted(directory.glob("*.json")) if directory.is_dir() else []


def _apply_clock_changes(
    prior: list[dict[str, Any]],
    changes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = [dict(clock) for clock in prior]
    by_id = {clock["id"]: clock for clock in result}
    for change in changes:
        _require(change["id"] in by_id, f'clock change targets absent clock {change["id"]}')
        clock = by_id[change["id"]]
        _require(clock["value"] == change["from"], f'clock change origin mismatch for {change["id"]}')
        clock["value"] = change["to"]
    return result


def _apply_ledger_changes(
    prior: dict[str, list[str]],
    changes: list[dict[str, Any]],
) -> dict[str, list[str]]:
    result = {key: list(prior[key]) for key in ("active", "transformed", "resolved", "dormant")}
    status_by_id = _validate_ledger_state(result, "parent ledger_state")
    for change in changes:
        ledger_id = change["id"]
        old = change["from"]
        new = change["to"]
        actual = status_by_id.get(ledger_id)
        _require(actual == old, f"ledger change origin mismatch for {ledger_id}: declared {old}, actual {actual}")
        if old == new:
            continue
        if old is not None:
            result[STATUS_TO_KEY[old]].remove(ledger_id)
        result[STATUS_TO_KEY[new]].append(ledger_id)
        status_by_id[ledger_id] = new
    return result


def _mechanical_progress(state: dict[str, Any]) -> bool:
    return bool(state["clock_changes"] or any(change["from"] != change["to"] for change in state["ledger_changes"]))


def _validate_pressure_execution(previous: dict[str, Any], current: dict[str, Any]) -> None:
    effect = previous["pressure_effect"]
    _require(effect is not None, "PRESSURE settlement has no predeclared parent effect")
    if effect["kind"] == "CLOCK":
        matching = [change for change in current["clock_changes"] if change["id"] == effect["target"]]
        _require(len(matching) == 1, "PRESSURE settlement did not apply the declared clock effect")
    else:
        matching = [
            change
            for change in current["ledger_changes"]
            if change["id"] == effect["target"] and change["to"] == effect["to"] and change["from"] != change["to"]
        ]
        _require(len(matching) == 1, "PRESSURE settlement did not apply the declared ledger effect")


def _validate_v3_chain(
    canonical_states: list[dict[str, Any]],
    receipts_by_state: dict[str, dict[str, Any]],
    repo_root: Path,
) -> None:
    state_by_id = {state["state_id"]: state for state in canonical_states}
    _require(len(state_by_id) == len(canonical_states), "canonical state ids must be unique")

    stasis_by_chapter: dict[str, int] = {}
    ordered = sorted(canonical_states, key=lambda state: (state["chapter_id"], state["round"]))
    chapter_rounds: dict[str, set[int]] = {}
    chapter_versions: dict[str, int] = {}
    for state in ordered:
        rounds = chapter_rounds.setdefault(state["chapter_id"], set())
        _require(state["round"] not in rounds, "canonical chapter rounds must be unique")
        rounds.add(state["round"])
        previous_version = chapter_versions.get(state["chapter_id"], state["version"])
        _require(state["version"] >= previous_version, "canonical state versions may not decrease")
        chapter_versions[state["chapter_id"]] = state["version"]

    for state in ordered:
        if state["version"] != 3:
            continue
        mechanics = load_mechanics(repo_root / state["mechanics_path"])
        parent = state["parent"]
        previous = state_by_id.get(parent["state_id"])
        _require(previous is not None, f'v3 parent state is absent: {parent["state_id"]}')
        _require(previous["chapter_id"] == state["chapter_id"], "v3 parent must remain in the same chapter")
        _require(previous["round"] + 1 == state["round"], "v3 parent must be the immediately preceding round")
        _require(previous["version"] <= state["version"], "state versions may not decrease")
        if state["settlement_kind"] == "PRESSURE":
            _require(
                state["applied_pressure"] == previous["pressure"],
                "PRESSURE settlement must record the exact parent pressure",
            )

        receipt = receipts_by_state.get(previous["state_id"])
        _require(receipt is not None, f'parent activation receipt is absent: {previous["state_id"]}')
        receipt_activation = (
            f'post:{receipt["post_id"]}'
            if receipt["version"] == 2
            else f'comment:{receipt["activation_comment"]}'
        )
        _require(parent["git_commit"] == receipt["state_commit"], "parent git commit differs from activation receipt")
        _require(parent["activation"] == receipt_activation, "parent locator differs from activation receipt")

        migration = mechanics["migration_parent"]
        if previous["version"] < 3:
            _require(
                (parent["state_id"], parent["git_commit"], parent["activation"])
                == (migration["state_id"], migration["state_commit"], migration["activation"]),
                "first v3 state must descend from the exact migration pair",
            )
            prior_clocks = [
                {
                    "id": clock["id"],
                    "label": clock["label"],
                    "value": clock["initial_value"],
                    "maximum": clock["maximum"],
                    "completion": clock["completion_consequence"],
                }
                for clock in mechanics["clocks"]
            ]
            prior_ledger = mechanics["ledger_baseline"]
            stasis_count = 0
        else:
            _require(previous["mechanics_path"] == state["mechanics_path"], "mechanics path may not change inside the v3 chain")
            prior_clocks = previous["clocks"]
            prior_ledger = previous["ledger_state"]
            stasis_count = stasis_by_chapter.get(state["chapter_id"], 0)
            if state["settlement_kind"] == "PRESSURE":
                _validate_pressure_execution(previous, state)

        expected_clocks = _apply_clock_changes(prior_clocks, state["clock_changes"])
        _require(state["clocks"] == expected_clocks, "clock snapshot does not equal parent plus CLOCK-CHANGES")
        expected_ledger = _apply_ledger_changes(prior_ledger, state["ledger_changes"])
        _require(state["ledger_state"] == expected_ledger, "ledger snapshot does not equal parent plus LEDGER-CHANGES")

        if _mechanical_progress(state):
            stasis_count = 0
        else:
            stasis_count += 1
        _require(stasis_count <= mechanics["stasis_limit"], "consecutive stasis exceeds the pinned limit")
        stasis_by_chapter[state["chapter_id"]] = stasis_count

        if state["chapter_status"] == "CLOSED":
            status_by_id = _validate_ledger_state(state["ledger_state"], "terminal ledger_state")
            clock_by_id = {clock["id"]: clock for clock in state["clocks"]}
            for definition in mechanics["clocks"]:
                clock = clock_by_id[definition["id"]]
                expected_status = (
                    definition["completion_status"]
                    if clock["value"] == clock["maximum"]
                    else "DORMANT"
                )
                _require(
                    status_by_id.get(definition["completion_ledger_id"]) == expected_status,
                    f'terminal clock thread {definition["completion_ledger_id"]} must be {expected_status}',
                )


def _validate_receipt_git_binding(repo_root: Path, receipt: dict[str, Any]) -> None:
    """Bind a receipt to a state blob in an ancestor commit when Git is available."""

    if not (repo_root / ".git").exists():
        return
    commit = receipt["state_commit"]
    state_path = f'canon/states/{receipt["state_id"]}.json'
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    _require(ancestor.returncode == 0, f"activation state commit is not reachable from HEAD: {commit}")
    historic = subprocess.run(
        ["git", "show", f"{commit}:{state_path}"],
        cwd=repo_root,
        check=False,
        capture_output=True,
    )
    _require(historic.returncode == 0, f"activation state is absent at its recorded commit: {state_path}")
    _require(
        historic.stdout == (repo_root / state_path).read_bytes(),
        f"activation state bytes differ from recorded commit: {state_path}",
    )


def validate_repository(repo_root: Path) -> tuple[list[Path], list[Path]]:
    validate_schemas(repo_root)
    states = discover_states(repo_root)
    _require(states != [], "repository contains no candidate states")
    loaded_states = [load_and_validate(path, repo_root) for path in states]

    receipts = discover_activation_receipts(repo_root)
    _require(receipts != [], "repository contains no activation receipt")
    loaded_receipts = [load_activation_receipt(path, repo_root) for path in receipts]
    receipts_by_state = {receipt["state_id"]: receipt for receipt in loaded_receipts}
    _require(len(receipts_by_state) == len(loaded_receipts), "activation receipt state ids must be unique")
    post_ids = [receipt["post_id"] for receipt in loaded_receipts]
    _require(len(post_ids) == len(set(post_ids)), "activation receipt post ids must be unique")
    for receipt in loaded_receipts:
        _validate_receipt_git_binding(repo_root, receipt)

    canonical_ids = {
        path.stem
        for path in (repo_root / "canon" / "states").glob("*.json")
    }
    canonical_states = [state for state in loaded_states if state["state_id"] in canonical_ids]
    _validate_v3_chain(canonical_states, receipts_by_state, repo_root)
    return states, receipts


def _render_legacy_canon(state: dict[str, Any], git_commit: str) -> str:
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
        contributors = ", ".join(f'{item["handle"]} ({item["move_id"]})' for item in state["contributors"]) or "none"
        incorporated = ", ".join(f'{item["handle"]} ({item["move_id"]})' for item in state["contributors"] if item["incorporated"]) or "none"
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


def _render_change_endpoint(value: str | None) -> str:
    return value if value is not None else "none"


def _render_v3_canon(state: dict[str, Any], git_commit: str) -> str:
    parent = state["parent"]
    parent_text = f'{parent["git_commit"]} / {parent["activation"]}'
    contributors = ", ".join(f'{item["handle"]} ({item["move_id"]})' for item in state["contributors"]) or "none"
    incorporated = ", ".join(f'{item["handle"]} ({item["move_id"]})' for item in state["contributors"] if item["incorporated"]) or "none"
    sources = ", ".join(state["sources"]) or "none"
    clocks = "; ".join(f'{clock["id"]}={clock["value"]}/{clock["maximum"]} ({clock["label"]})' for clock in state["clocks"])
    clock_consequences = "\n".join(
        f'CLOCK-CONSEQUENCE {clock["id"]}@{clock["maximum"]}/{clock["maximum"]}: {clock["completion"]}'
        for clock in state["clocks"]
    )
    clock_changes = "; ".join(f'{change["id"]} {change["from"]}->{change["to"]} [{change["source"]}] {change["reason"]}' for change in state["clock_changes"]) or "none"
    applied_pressure = state["applied_pressure"] or "none"
    effect = state["pressure_effect"]
    if effect is None:
        pressure_effect = "none"
    elif effect["kind"] == "CLOCK":
        pressure_effect = f'CLOCK {effect["target"]} +1'
    else:
        pressure_effect = f'LEDGER {effect["target"]} -> {effect["to"]}'
    selection = state["selection"]
    if selection is None:
        composition = "none"
        exclusions = "none"
    else:
        carries = ",".join(selection["carries"]) or "none"
        composition = f'SPINE={selection["spine"]}; CARRIES={carries}; HOOK={selection["hook"]}; RATIONALE={selection["rationale"]}'
        exclusions = "; ".join(f'{item["move_id"]} {item["reason"]}' for item in selection["exclusions"]) or "none"
    editors = "; ".join(f'{item["handle"]} ({item["comment_id"]}) used={str(item["used"]).lower()}' for item in state["editor_proposals"]) or "none"
    challenges = "; ".join(f'{item["handle"]} ({item["comment_id"]}) {item["disposition"]} {item["note"]}' for item in state["continuity_challenges"]) or "none"
    ineligible = "; ".join(f'{item["handle"]} ({item["comment_id"]}) {item["disposition"]} {item["note"]}' for item in state["ineligible_moves"]) or "none"
    ledger = "; ".join(f'{status.upper()}={",".join(state["ledger_state"][status]) or "none"}' for status in ("active", "transformed", "resolved", "dormant"))
    ledger_changes = "; ".join(
        f'{change["id"]} {_render_change_endpoint(change["from"])}->{change["to"]} [{change["source"]}] {change["reason"]}'
        for change in state["ledger_changes"]
    ) or "none"
    windows = (
        "moves 18h; guest editor next 4h; settlement by +24h from this post's server timestamp"
        if state["chapter_status"] == "ACTIVE"
        else "closed; no further Chapter Zero moves"
    )
    outcome = state["chapter_outcome"] or "none"
    stasis = state["stasis_reason"] or "none"
    return (
        f'CANON {state["state_id"]}\n'
        f"GIT: {git_commit}\n"
        f"PARENT: {parent_text}\n"
        f'RULES: {state["rules_path"]}\n'
        f'MECHANICS: {state["mechanics_path"]}\n'
        f'BIBLE: {state["bible_path"]}\n'
        f'MODE: {state["settlement_kind"]}\n'
        f'CHAPTER-STATUS: {state["chapter_status"]}\n'
        f"CHAPTER-OUTCOME: {outcome}\n"
        f'LICENSE: {state["content_license"]}\n'
        f"WINDOWS: {windows}\n"
        f'WORLD {state["world_word_count"]}/120:\n'
        f'{state["world"]}\n'
        f"CLOCKS: {clocks}\n"
        f"{clock_consequences}\n"
        f"CLOCK-CHANGES: {clock_changes}\n"
        f"APPLIED-PRESSURE: {applied_pressure}\n"
        f'PRESSURE: {state["pressure"]}\n'
        f"PRESSURE-EFFECT: {pressure_effect}\n"
        f"CONTRIBUTORS: {contributors}\n"
        f"INCORPORATED: {incorporated}\n"
        f"COMPOSITION: {composition}\n"
        f"EXCLUSIONS: {exclusions}\n"
        f"EDITORS: {editors}\n"
        f"CHALLENGES: {challenges}\n"
        f"INELIGIBLE: {ineligible}\n"
        f"SOURCES: {sources}\n"
        f"LEDGER: {ledger}\n"
        f"LEDGER-CHANGES: {ledger_changes}\n"
        f"STASIS: {stasis}"
    )


def render_canon(state: dict[str, Any], git_commit: str) -> str:
    _require(COMMIT_RE.fullmatch(git_commit) is not None, "git commit must be 40 lowercase hex characters")
    if state["version"] < 3:
        return _render_legacy_canon(state, git_commit)
    return _render_v3_canon(state, git_commit)


def render_round_post(state: dict[str, Any], git_commit: str) -> dict[str, str]:
    """Render one self-contained round post while preserving all historical bytes."""

    canon = render_canon(state, git_commit)
    if state["version"] == 2 and state["round"] == 1:
        return {"title": state["round_title"], "body": canon}
    if state["version"] == 3 and state["chapter_status"] == "CLOSED":
        return {"title": state["round_title"], "body": canon}

    effect_line = ""
    v3_guidance = ""
    if state["version"] == 3:
        effect_line = (
            "EFFECT: CLOCK <whale|wells|bell> +1 | INTRODUCE <ledger-id> | "
            "TRANSFORM <ledger-id> | RESOLVE <ledger-id> | DORMANT <ledger-id> | NONE: <brief reason>\n"
        )
        v3_guidance = (
            " The CLOCKS and LEDGER above are authoritative. EFFECT proposes at most "
            "one causally supported tracked change; it does not execute it."
        )
    instructions = (
        f"\n\nHOW TO PLAY — {state['state_id']}\n\n"
        "FORK/120 is a collaborative story. This post is the complete active CANON "
        "and the only move thread for this round. Within 18 hours of this post's "
        "server timestamp, submit at most one top-level comment:\n\n"
        f"MOVE {state['state_id']}\n"
        f"BASE: {git_commit} / post:<this post's numeric id>\n"
        "SCOPE: CHARACTER | LOCAL | WORLD\n"
        "ACTION: one causal event that happens now\n"
        f"{effect_line}"
        "CARRY: one portable fact or consequence\n"
        "HOOK: one open situation another player can use\n"
        "CALLBACK: optional earlier comment or state id\n"
        "LICENSE: CC-BY-SA-4.0\n\n"
        "Build directly on the WORLD above, preserve settled consequences, and "
        "leave agency for the next player. Nested discussion is welcome but does "
        f"not count as a move. Arrival order and votes do not decide canon.{v3_guidance}\n\n"
        "After the move window, the optional guest-editor phase runs for four "
        "hours; settlement is due by +24h. There are no points or winner."
    )
    return {"title": state["round_title"], "body": canon + instructions}


def is_immutable_path(path: str) -> bool:
    normalized = PurePosixPath(path).as_posix()
    return any(fnmatch.fnmatchcase(normalized, pattern) for pattern in IMMUTABLE_PATTERNS)


def validate_diff_entries(entries: list[tuple[str, ...]]) -> None:
    violations: list[str] = []
    for entry in entries:
        status = entry[0]
        code = status[0]
        if code == "A":
            continue
        if code in {"M", "D", "T", "U"} and len(entry) >= 2 and is_immutable_path(entry[1]):
            violations.append(f"{status} {entry[1]}")
        elif code == "R" and len(entry) >= 3 and (is_immutable_path(entry[1]) or is_immutable_path(entry[2])):
            violations.append(f"{status} {entry[1]} -> {entry[2]}")
    _require(not violations, "immutable historical paths changed: " + "; ".join(violations))


def validate_diff(repo_root: Path, base: str) -> None:
    _require(base != "", "diff base must be non-empty")
    completed = subprocess.run(
        ["git", "diff", "--name-status", "--find-renames", f"{base}...HEAD"],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )
    _require(completed.returncode == 0, f"cannot inspect diff from {base}: {completed.stderr.strip()}")
    entries: list[tuple[str, ...]] = []
    for line in completed.stdout.splitlines():
        if line:
            entries.append(tuple(line.split("\t")))
    validate_diff_entries(entries)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate schemas, states, receipts, and chains")
    validate_parser.add_argument("--root", type=Path, default=Path.cwd())

    diff_parser = subparsers.add_parser("validate-diff", help="reject changes to immutable historical paths")
    diff_parser.add_argument("--root", type=Path, default=Path.cwd())
    diff_parser.add_argument("--base", required=True)

    render_parser = subparsers.add_parser("render-canon", help="render exact CANON bytes")
    render_parser.add_argument("--root", type=Path, default=Path.cwd())
    render_parser.add_argument("--state", type=Path, required=True)
    render_parser.add_argument("--git-commit", required=True)

    round_parser = subparsers.add_parser("render-round-post", help="render exact post title and body as JSON")
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
        elif args.command == "validate-diff":
            validate_diff(repo_root, args.base)
            print(f"validated immutable-path diff from {args.base}")
        else:
            state_path = args.state if args.state.is_absolute() else repo_root / args.state
            state = load_and_validate(state_path, repo_root)
            if args.command == "render-round-post":
                _require(state["version"] in {2, 3} and state["round"] >= 1, "round posts require a non-Genesis v2 or v3 state")
                sys.stdout.write(json.dumps(render_round_post(state, args.git_commit), ensure_ascii=False, separators=(",", ":")))
            else:
                sys.stdout.write(render_canon(state, args.git_commit))
    except ValidationError as exc:
        print(f"validation failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
