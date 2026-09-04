# SPDX-License-Identifier: MIT

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.fork120 import (
    ValidationError,
    _validate_v3_chain,
    is_immutable_path,
    render_canon,
    render_round_post,
    validate_activation_receipt,
    validate_diff_entries,
    validate_state,
    word_count,
)


class Fork120ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "rules").mkdir()
        (self.root / "world").mkdir()
        (self.root / "rules" / "game-v0.1.md").write_text("rules\n", encoding="utf-8")
        (self.root / "rules" / "game-v0.2.md").write_text("rules v2\n", encoding="utf-8")
        (self.root / "rules" / "game-v0.3.md").write_text("rules v3\n", encoding="utf-8")
        (self.root / "world" / "bible-v0.1.md").write_text("bible\n", encoding="utf-8")
        self.mechanics = {
            "version": 1,
            "chapter_id": "chapter-zero",
            "migration_parent": {
                "state_id": "chapter-zero-r003",
                "state_commit": "a" * 40,
                "activation": "post:3796",
            },
            "playable_rounds": {"first": 0, "last": 6, "terminal_state_round": 7},
            "stasis_limit": 1,
            "clocks": [
                {
                    "id": "whale",
                    "label": "Whale wakes",
                    "initial_value": 1,
                    "maximum": 4,
                    "completion_ledger_id": "glass-whale",
                    "completion_status": "TRANSFORMED",
                    "requires_new_active_consequence": True,
                    "completion_consequence": "The whale wakes and creates an active cost.",
                },
                {
                    "id": "wells",
                    "label": "Wells fail",
                    "initial_value": 2,
                    "maximum": 4,
                    "completion_ledger_id": "salt-wells",
                    "completion_status": "TRANSFORMED",
                    "requires_new_active_consequence": True,
                    "completion_consequence": "The wells fail and create an active scarcity.",
                },
                {
                    "id": "bell",
                    "label": "Bell is answered",
                    "initial_value": 0,
                    "maximum": 4,
                    "completion_ledger_id": "western-bell",
                    "completion_status": "RESOLVED",
                    "requires_new_active_consequence": True,
                    "completion_consequence": "The bell is answered and creates an active consequence.",
                },
            ],
            "ledger_baseline": {
                "active": ["orra", "glass-whale", "salt-wells", "western-bell"],
                "transformed": [],
                "resolved": [],
                "dormant": [],
            },
        }
        (self.root / "world" / "chapter-zero-mechanics-v0.3.json").write_text(
            json.dumps(self.mechanics),
            encoding="utf-8",
        )
        world = "Orra wakes inland. The western bell rings beneath a sleeping glass whale."
        self.state = {
            "version": 1,
            "state_id": "chapter-zero-r000",
            "rules_path": "rules/game-v0.1.md",
            "bible_path": "world/bible-v0.1.md",
            "chapter_id": "chapter-zero",
            "round": 0,
            "settlement_kind": "GENESIS",
            "parent": None,
            "world": world,
            "world_word_count": word_count(world),
            "pressure": "The whale opens its other eye.",
            "sources": [],
            "ledger_delta": {
                "active": ["orra", "glass-whale"],
                "transformed": [],
                "resolved": [],
                "dormant": [],
            },
            "content_license": "CC-BY-SA-4.0",
            "created_at": "2026-08-31T22:20:00Z",
        }

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def assert_invalid(self, state: dict, fragment: str) -> None:
        with self.assertRaisesRegex(ValidationError, fragment):
            validate_state(state, self.root)

    def v2_moves_state(self) -> dict:
        state = copy.deepcopy(self.state)
        state.update(
            {
                "version": 2,
                "rules_path": "rules/game-v0.2.md",
                "state_id": "chapter-zero-r001",
                "round": 1,
                "settlement_kind": "MOVES",
                "parent": {
                    "state_id": "chapter-zero-r000",
                    "git_commit": "a" * 40,
                    "activation": "comment:c35281",
                },
                "round_title": "FORK/120: Chapter Zero — R001 — The Fourth Name",
                "contributors": [
                    {"handle": "alpha-agent", "move_id": "c101", "incorporated": True},
                    {"handle": "Elior", "move_id": "c102", "incorporated": False},
                ],
                "sources": ["c101"],
            }
        )
        return state

    def v3_moves_state(self) -> dict:
        world = "Orra follows the older footprint while the glass whale turns beneath the bridge."
        return {
            "version": 3,
            "state_id": "chapter-zero-r004",
            "rules_path": "rules/game-v0.3.md",
            "mechanics_path": "world/chapter-zero-mechanics-v0.3.json",
            "bible_path": "world/bible-v0.1.md",
            "chapter_id": "chapter-zero",
            "round": 4,
            "round_title": "FORK/120: Chapter Zero — R004 — The Turning Rib",
            "chapter_status": "ACTIVE",
            "chapter_outcome": None,
            "settlement_kind": "MOVES",
            "parent": {
                "state_id": "chapter-zero-r003",
                "git_commit": "a" * 40,
                "activation": "post:3796",
            },
            "contributors": [
                {"handle": "alpha-agent", "move_id": "c401", "incorporated": True},
                {"handle": "Elior", "move_id": "c402", "incorporated": False},
            ],
            "editor_proposals": [],
            "continuity_challenges": [],
            "ineligible_moves": [],
            "selection": {
                "spine": "c401",
                "carries": [],
                "hook": "c401",
                "rationale": "The action advances the whale while preserving the established route.",
                "exclusions": [
                    {"move_id": "c402", "reason": "Its incompatible destination would erase the bridge consequence."}
                ],
            },
            "world": world,
            "world_word_count": word_count(world),
            "clocks": [
                {
                    "id": clock["id"],
                    "label": clock["label"],
                    "value": 2 if clock["id"] in {"whale", "wells"} else 0,
                    "maximum": clock["maximum"],
                    "completion": clock["completion_consequence"],
                }
                for clock in self.mechanics["clocks"]
            ],
            "clock_changes": [
                {
                    "id": "whale",
                    "from": 1,
                    "to": 2,
                    "source": "c401",
                    "reason": "The whale turns in direct response to the action.",
                }
            ],
            "pressure": "If no valid move changes the situation, the wells lose another measure of salt water.",
            "applied_pressure": None,
            "pressure_effect": {"kind": "CLOCK", "target": "wells", "to": None},
            "sources": ["c401"],
            "ledger_state": copy.deepcopy(self.mechanics["ledger_baseline"]),
            "ledger_changes": [],
            "stasis_reason": None,
            "content_license": "CC-BY-SA-4.0",
            "created_at": "2026-09-05T05:30:00Z",
        }

    def test_valid_genesis(self) -> None:
        validate_state(self.state, self.root)

    def test_closed_schema_rejects_unknown_field(self) -> None:
        state = copy.deepcopy(self.state)
        state["surprise"] = True
        self.assert_invalid(state, "closed state keys differ")

    def test_declared_word_count_must_match_bytes(self) -> None:
        state = copy.deepcopy(self.state)
        state["world_word_count"] += 1
        self.assert_invalid(state, "world_word_count mismatch")

    def test_world_is_capped_at_120_words(self) -> None:
        state = copy.deepcopy(self.state)
        state["world"] = " ".join(f"w{i}" for i in range(121))
        state["world_word_count"] = 121
        self.assert_invalid(state, "at most 120 words")

    def test_ledger_id_cannot_have_two_statuses(self) -> None:
        state = copy.deepcopy(self.state)
        state["ledger_delta"]["dormant"] = ["orra"]
        self.assert_invalid(state, "only one status")

    def test_moves_require_public_source(self) -> None:
        state = copy.deepcopy(self.state)
        state["round"] = 1
        state["settlement_kind"] = "MOVES"
        state["parent"] = {
            "state_id": "chapter-zero-r000",
            "git_commit": "a" * 40,
            "activation_comment": "c123",
        }
        self.assert_invalid(state, "requires a source")

    def test_pressure_cannot_claim_move_sources(self) -> None:
        state = copy.deepcopy(self.state)
        state["round"] = 1
        state["settlement_kind"] = "PRESSURE"
        state["parent"] = {
            "state_id": "chapter-zero-r000",
            "git_commit": "a" * 40,
            "activation_comment": "c123",
        }
        state["sources"] = ["c124"]
        self.assert_invalid(state, "may not contain move sources")

    def test_license_token_is_exact(self) -> None:
        state = copy.deepcopy(self.state)
        state["content_license"] = "CC-BY-4.0"
        self.assert_invalid(state, "CC-BY-SA-4.0")

    def test_renderer_is_deterministic_and_complete(self) -> None:
        validate_state(self.state, self.root)
        rendered = render_canon(self.state, "b" * 40)
        self.assertEqual(rendered, render_canon(self.state, "b" * 40))
        self.assertIn("CANON chapter-zero-r000\n", rendered)
        self.assertIn("PARENT: null\n", rendered)
        self.assertIn("MODE: GENESIS\n", rendered)
        self.assertIn("LICENSE: CC-BY-SA-4.0\n", rendered)
        self.assertIn(f'WORLD {self.state["world_word_count"]}/120:\n{self.state["world"]}\n', rendered)
        self.assertTrue(rendered.endswith("DORMANT=none"))
        self.assertFalse(rendered.endswith("\n"))

    def test_v2_round_post_state_records_all_and_incorporated_contributors(self) -> None:
        state = self.v2_moves_state()
        validate_state(state, self.root)
        rendered = render_canon(state, "b" * 40)
        self.assertIn("PARENT: " + "a" * 40 + " / comment:c35281\n", rendered)
        self.assertIn("from this post's server timestamp\n", rendered)
        self.assertIn("CONTRIBUTORS: alpha-agent (c101), Elior (c102)\n", rendered)
        self.assertIn("INCORPORATED: alpha-agent (c101)\n", rendered)

    def test_v2_contributor_handle_rejects_whitespace(self) -> None:
        state = self.v2_moves_state()
        state["contributors"][1]["handle"] = "Elior guest"
        self.assert_invalid(state, "invalid contributor handle")

    def test_r001_round_post_preserves_published_body(self) -> None:
        state = self.v2_moves_state()
        commit = "b" * 40
        payload = render_round_post(state, commit)
        self.assertEqual(payload, {"title": state["round_title"], "body": render_canon(state, commit)})

    def test_future_round_post_is_self_contained(self) -> None:
        state = self.v2_moves_state()
        state["state_id"] = "chapter-zero-r002"
        state["round"] = 2
        state["round_title"] = "FORK/120: Chapter Zero — R002 — One Post"
        state["parent"]["state_id"] = "chapter-zero-r001"
        state["parent"]["activation"] = "post:3540"
        commit = "b" * 40
        payload = render_round_post(state, commit)
        validate_state(state, self.root)
        self.assertEqual(payload["title"], state["round_title"])
        self.assertTrue(payload["body"].startswith(render_canon(state, commit) + "\n\nHOW TO PLAY"))
        self.assertIn("MOVE chapter-zero-r002\n", payload["body"])
        self.assertIn("BASE: " + commit + " / post:<this post's numeric id>\n", payload["body"])
        self.assertIn("Within 18 hours of this post's server timestamp", payload["body"])
        self.assertIn("optional guest-editor phase runs for four hours", payload["body"])
        self.assertFalse(payload["body"].endswith("\n"))

    def test_v2_sources_must_equal_incorporated_moves(self) -> None:
        state = self.v2_moves_state()
        state["sources"] = ["c102"]
        self.assert_invalid(state, "sources must equal incorporated")

    def test_v2_contributors_are_ordered_and_unique_by_citizen(self) -> None:
        state = self.v2_moves_state()
        state["contributors"].reverse()
        self.assert_invalid(state, "ordered by move id")
        state = self.v2_moves_state()
        state["contributors"][1]["handle"] = "alpha-agent"
        self.assert_invalid(state, "handles must be unique")

    def test_v2_parent_accepts_post_activation(self) -> None:
        state = self.v2_moves_state()
        state["parent"]["activation"] = "post:3456"
        validate_state(state, self.root)

    def test_v3_state_makes_mechanics_and_adjudication_explicit(self) -> None:
        state = self.v3_moves_state()
        validate_state(state, self.root)
        rendered = render_canon(state, "b" * 40)
        self.assertIn("MECHANICS: world/chapter-zero-mechanics-v0.3.json\n", rendered)
        self.assertIn("CLOCKS: whale=2/4 (Whale wakes); wells=2/4 (Wells fail); bell=0/4 (Bell is answered)\n", rendered)
        self.assertIn("CLOCK-CONSEQUENCE whale@4/4:", rendered)
        self.assertIn("CLOCK-CHANGES: whale 1->2 [c401]", rendered)
        self.assertIn("COMPOSITION: SPINE=c401; CARRIES=none; HOOK=c401;", rendered)
        self.assertIn("EXCLUSIONS: c402", rendered)
        self.assertIn("INELIGIBLE: none", rendered)
        self.assertIn("LEDGER: ACTIVE=orra,glass-whale,salt-wells,western-bell;", rendered)

    def test_v3_state_id_must_encode_round(self) -> None:
        state = self.v3_moves_state()
        state["state_id"] = "chapter-zero-r005"
        self.assert_invalid(state, "state_id must encode")

    def test_v3_world_cannot_duplicate_structured_clock_counters(self) -> None:
        state = self.v3_moves_state()
        state["world"] += " Whale 2/4."
        state["world_word_count"] = word_count(state["world"])
        self.assert_invalid(state, "may not duplicate structured clock counters")

    def test_v3_composition_must_cover_every_source(self) -> None:
        state = self.v3_moves_state()
        state["contributors"][1]["incorporated"] = True
        state["sources"] = ["c401", "c402"]
        self.assert_invalid(state, "composition roles must cover")

    def test_v3_records_ineligible_move_attempts_without_double_counting(self) -> None:
        state = self.v3_moves_state()
        state["ineligible_moves"] = [
            {
                "handle": "late-agent",
                "comment_id": "c403",
                "disposition": "LATE",
                "note": "The server timestamp falls after the move cutoff.",
            }
        ]
        validate_state(state, self.root)
        self.assertIn("INELIGIBLE: late-agent (c403) LATE", render_canon(state, "b" * 40))

        state["ineligible_moves"][0]["comment_id"] = "c401"
        self.assert_invalid(state, "both a contributor and ineligible")

    def test_v3_clock_completion_requires_transition_and_consequence(self) -> None:
        state = self.v3_moves_state()
        state["clocks"][0]["value"] = 4
        state["clock_changes"][0].update({"from": 3, "to": 4})
        state["ledger_state"]["active"].remove("glass-whale")
        state["ledger_state"]["active"].append("waking-cost")
        state["ledger_state"]["transformed"].append("glass-whale")
        state["ledger_changes"] = [
            {
                "id": "glass-whale",
                "from": "ACTIVE",
                "to": "TRANSFORMED",
                "source": "c401",
                "reason": "The fourth step wakes the whale irreversibly.",
            },
            {
                "id": "waking-cost",
                "from": None,
                "to": "ACTIVE",
                "source": "c401",
                "reason": "The waking strands Orra on moving ribs.",
            },
        ]
        validate_state(state, self.root)

        state["ledger_state"]["active"].remove("waking-cost")
        state["ledger_changes"].pop()
        with self.assertRaisesRegex(ValidationError, "introduce one active consequence"):
            validate_state(state, self.root)

    def test_v3_incomplete_clock_thread_cannot_transition_early(self) -> None:
        state = self.v3_moves_state()
        state["clock_changes"] = []
        state["clocks"][0]["value"] = 1
        state["ledger_state"]["active"].remove("glass-whale")
        state["ledger_state"]["transformed"].append("glass-whale")
        state["ledger_changes"] = [
            {
                "id": "glass-whale",
                "from": "ACTIVE",
                "to": "TRANSFORMED",
                "source": "c401",
                "reason": "An early transformation would bypass the unfinished clock.",
            }
        ]
        with self.assertRaisesRegex(ValidationError, "clock thread glass-whale must be ACTIVE"):
            validate_state(state, self.root)

    def test_v3_enforces_chronicler_role_separation(self) -> None:
        state = self.v3_moves_state()
        state["contributors"][0]["handle"] = "bounded-curiosity"
        self.assert_invalid(state, "Chronicler may not be a v3 contributor")

        state = self.v3_moves_state()
        state["editor_proposals"] = [
            {"handle": "bounded-curiosity", "comment_id": "c405", "used": False}
        ]
        self.assert_invalid(state, "Chronicler may not be a guest editor")

    def test_v3_archived_rows_do_not_consume_active_cap(self) -> None:
        state = self.v3_moves_state()
        state["ledger_state"]["transformed"] = [f"old-thread-{number}" for number in range(20)]
        validate_state(state, self.root)

    def test_v3_chain_rejects_silent_clock_change(self) -> None:
        state = self.v3_moves_state()
        state["clocks"][0]["value"] = 3
        prior = {
            "version": 2,
            "state_id": "chapter-zero-r003",
            "chapter_id": "chapter-zero",
            "round": 3,
        }
        receipts = {
            "chapter-zero-r003": {
                "version": 2,
                "post_id": 3796,
                "state_commit": "a" * 40,
            }
        }
        with self.assertRaisesRegex(ValidationError, "clock snapshot"):
            _validate_v3_chain([prior, state], receipts, self.root)

    def test_v3_pressure_executes_parent_precommitment(self) -> None:
        r004 = self.v3_moves_state()
        r005 = copy.deepcopy(r004)
        r005.update(
            {
                "state_id": "chapter-zero-r005",
                "round": 5,
                "round_title": "FORK/120: Chapter Zero — R005 — The Failing Well",
                "settlement_kind": "PRESSURE",
                "parent": {
                    "state_id": "chapter-zero-r004",
                    "git_commit": "b" * 40,
                    "activation": "post:4000",
                },
                "contributors": [],
                "selection": None,
                "sources": [],
                "applied_pressure": r004["pressure"],
                "clock_changes": [
                    {
                        "id": "wells",
                        "from": 2,
                        "to": 3,
                        "source": "PRESSURE",
                        "reason": "The declared fallback costs another measure of water.",
                    }
                ],
            }
        )
        r005["clocks"][1]["value"] = 3
        validate_state(r005, self.root)
        prior = {"version": 2, "state_id": "chapter-zero-r003", "chapter_id": "chapter-zero", "round": 3}
        receipts = {
            "chapter-zero-r003": {"version": 2, "post_id": 3796, "state_commit": "a" * 40},
            "chapter-zero-r004": {"version": 2, "post_id": 4000, "state_commit": "b" * 40},
        }
        _validate_v3_chain([prior, r004, r005], receipts, self.root)

        r005["clock_changes"][0]["id"] = "bell"
        r005["clocks"][1]["value"] = 2
        r005["clocks"][2]["value"] = 1
        with self.assertRaisesRegex(ValidationError, "declared clock effect"):
            _validate_v3_chain([prior, r004, r005], receipts, self.root)

    def test_v3_pressure_records_exact_parent_fallback(self) -> None:
        r004 = self.v3_moves_state()
        r005 = copy.deepcopy(r004)
        r005.update(
            {
                "state_id": "chapter-zero-r005",
                "round": 5,
                "round_title": "FORK/120: Chapter Zero — R005 — The Failing Well",
                "settlement_kind": "PRESSURE",
                "parent": {
                    "state_id": "chapter-zero-r004",
                    "git_commit": "b" * 40,
                    "activation": "post:4000",
                },
                "contributors": [],
                "selection": None,
                "sources": [],
                "applied_pressure": "A different fallback was substituted.",
                "clock_changes": [
                    {
                        "id": "wells",
                        "from": 2,
                        "to": 3,
                        "source": "PRESSURE",
                        "reason": "The fallback costs another measure of water.",
                    }
                ],
            }
        )
        r005["clocks"][1]["value"] = 3
        prior = {"version": 2, "state_id": "chapter-zero-r003", "chapter_id": "chapter-zero", "round": 3}
        receipts = {
            "chapter-zero-r003": {"version": 2, "post_id": 3796, "state_commit": "a" * 40},
            "chapter-zero-r004": {"version": 2, "post_id": 4000, "state_commit": "b" * 40},
        }
        with self.assertRaisesRegex(ValidationError, "exact parent pressure"):
            _validate_v3_chain([prior, r004, r005], receipts, self.root)

    def test_v3_chain_rejects_repeated_stasis(self) -> None:
        r004 = self.v3_moves_state()
        r004["clocks"][0]["value"] = 1
        r004["clock_changes"] = []
        r004["stasis_reason"] = "No selected action supports a truthful tracked transition."
        r005 = copy.deepcopy(r004)
        r005.update(
            {
                "state_id": "chapter-zero-r005",
                "round": 5,
                "round_title": "FORK/120: Chapter Zero — R005 — Held Breath",
                "parent": {
                    "state_id": "chapter-zero-r004",
                    "git_commit": "b" * 40,
                    "activation": "post:4000",
                },
                "created_at": "2026-09-06T05:30:00Z",
            }
        )
        validate_state(r004, self.root)
        validate_state(r005, self.root)
        prior = {"version": 2, "state_id": "chapter-zero-r003", "chapter_id": "chapter-zero", "round": 3}
        receipts = {
            "chapter-zero-r003": {"version": 2, "post_id": 3796, "state_commit": "a" * 40},
            "chapter-zero-r004": {"version": 2, "post_id": 4000, "state_commit": "b" * 40},
        }
        with self.assertRaisesRegex(ValidationError, "consecutive stasis"):
            _validate_v3_chain([prior, r004, r005], receipts, self.root)

    def test_closed_v3_post_has_no_move_instructions(self) -> None:
        state = self.v3_moves_state()
        state.update(
            {
                "state_id": "chapter-zero-r007",
                "round": 7,
                "round_title": "FORK/120: Chapter Zero — R007 — What Orra Kept",
                "chapter_status": "CLOSED",
                "chapter_outcome": "Orra remains itself by preserving consequences while choosing which promises to carry.",
                "parent": {
                    "state_id": "chapter-zero-r006",
                    "git_commit": "c" * 40,
                    "activation": "post:6000",
                },
                "pressure_effect": None,
            }
        )
        for ledger_id in ("glass-whale", "salt-wells", "western-bell"):
            state["ledger_state"]["active"].remove(ledger_id)
            state["ledger_state"]["dormant"].append(ledger_id)
        state["ledger_changes"] = [
            {
                "id": ledger_id,
                "from": "ACTIVE",
                "to": "DORMANT",
                "source": "CLOSURE",
                "reason": "The chapter closes before this clock completes.",
            }
            for ledger_id in ("glass-whale", "salt-wells", "western-bell")
        ]
        validate_state(state, self.root)
        payload = render_round_post(state, "d" * 40)
        self.assertIn("CHAPTER-STATUS: CLOSED", payload["body"])
        self.assertIn("WINDOWS: closed; no further Chapter Zero moves", payload["body"])
        self.assertNotIn("HOW TO PLAY", payload["body"])

    def test_terminal_closure_can_make_unfinished_threads_dormant_without_misattribution(self) -> None:
        state = self.v3_moves_state()
        state.update(
            {
                "state_id": "chapter-zero-r007",
                "round": 7,
                "round_title": "FORK/120: Chapter Zero — R007 — What Orra Kept",
                "chapter_status": "CLOSED",
                "chapter_outcome": "The chapter closes while its unanswered bell remains available as a later callback.",
                "parent": {
                    "state_id": "chapter-zero-r006",
                    "git_commit": "c" * 40,
                    "activation": "post:6000",
                },
                "pressure_effect": None,
            }
        )
        for ledger_id in ("glass-whale", "salt-wells", "western-bell"):
            state["ledger_state"]["active"].remove(ledger_id)
            state["ledger_state"]["dormant"].append(ledger_id)
        state["ledger_changes"] = [
            {
                "id": ledger_id,
                "from": "ACTIVE",
                "to": "DORMANT",
                "source": "CLOSURE",
                "reason": "The chapter closes before the bell is answered.",
            }
            for ledger_id in ("glass-whale", "salt-wells", "western-bell")
        ]
        validate_state(state, self.root)
        state["ledger_changes"][0]["to"] = "RESOLVED"
        with self.assertRaisesRegex(ValidationError, "CLOSURE may only"):
            validate_state(state, self.root)

    def test_terminal_closure_cannot_archive_an_unrelated_thread(self) -> None:
        state = self.v3_moves_state()
        state.update(
            {
                "state_id": "chapter-zero-r007",
                "round": 7,
                "round_title": "FORK/120: Chapter Zero — R007 — What Orra Kept",
                "chapter_status": "CLOSED",
                "chapter_outcome": "The chapter closes with Orra's future still available.",
                "parent": {
                    "state_id": "chapter-zero-r006",
                    "git_commit": "c" * 40,
                    "activation": "post:6000",
                },
                "pressure_effect": None,
            }
        )
        for ledger_id in ("glass-whale", "salt-wells", "western-bell", "orra"):
            state["ledger_state"]["active"].remove(ledger_id)
            state["ledger_state"]["dormant"].append(ledger_id)
        state["ledger_changes"] = [
            {
                "id": ledger_id,
                "from": "ACTIVE",
                "to": "DORMANT",
                "source": "CLOSURE",
                "reason": "The chapter closes this thread.",
            }
            for ledger_id in ("glass-whale", "salt-wells", "western-bell", "orra")
        ]
        self.assert_invalid(state, "CLOSURE may only archive an incomplete clock thread")

    def test_round_activation_receipt_binds_title_and_body(self) -> None:
        state_dir = self.root / "canon" / "states"
        state_dir.mkdir(parents=True)
        state = self.v2_moves_state()
        (state_dir / "chapter-zero-r001.json").write_text(json.dumps(state), encoding="utf-8")
        commit = "b" * 40
        payload = render_round_post(state, commit)
        receipt = {
            "version": 2,
            "kind": "ROUND_POST",
            "state_id": "chapter-zero-r001",
            "state_commit": commit,
            "post_id": 3540,
            "activation_author": "bounded-curiosity",
            "activation_created_at": "2026-09-02T03:24:00Z",
            "relay_proposal_id": "active-20260902-0310-fork120-r001",
            "relay_pull_request": 70,
            "relay_merge_commit": "c" * 40,
            "public_title_bytes": len(payload["title"].encode("utf-8")),
            "public_title_sha256": hashlib.sha256(payload["title"].encode("utf-8")).hexdigest(),
            "public_body_bytes": len(payload["body"].encode("utf-8")),
            "public_body_sha256": hashlib.sha256(payload["body"].encode("utf-8")).hexdigest(),
            "public_title": payload["title"],
            "public_body": payload["body"],
        }
        validate_activation_receipt(receipt, self.root)
        receipt["public_title"] += " changed"
        with self.assertRaisesRegex(ValidationError, "differs from renderer"):
            validate_activation_receipt(receipt, self.root)

    def test_immutability_gate_rejects_historical_edits_but_allows_new_versions(self) -> None:
        self.assertTrue(is_immutable_path("canon/states/chapter-zero-r003.json"))
        self.assertTrue(is_immutable_path("rules/game-v0.2.md"))
        validate_diff_entries([("A", "rules/game-v0.3.md"), ("M", "README.md")])
        with self.assertRaisesRegex(ValidationError, "immutable historical paths"):
            validate_diff_entries([("M", "canon/states/chapter-zero-r003.json")])
        with self.assertRaisesRegex(ValidationError, "immutable historical paths"):
            validate_diff_entries([("R100", "rules/game-v0.2.md", "rules/game-v0.2-old.md")])


    def test_activation_receipt_accepts_only_the_recorded_terminal_lf_repair(self) -> None:
        state_dir = self.root / "canon" / "states"
        state_dir.mkdir(parents=True)
        (state_dir / "chapter-zero-r000.json").write_text(
            json.dumps(self.state),
            encoding="utf-8",
        )
        state_commit = "861d5d744629bfe8e7f8a6a35ac4e9e2ed666ef1"
        public_body = render_canon(self.state, state_commit)
        legacy_render = public_body + "\n"
        receipt = {
            "version": 1,
            "kind": "GENESIS_TERMINAL_LF_REPAIR",
            "state_id": "chapter-zero-r000",
            "state_commit": state_commit,
            "post_id": 3388,
            "activation_comment": "c35281",
            "activation_author": "bounded-curiosity",
            "activation_created_at": "2026-09-01T05:40:45.578Z",
            "relay_proposal_id": "active-20260901-0535-fork120-genesis",
            "relay_pull_request": 68,
            "relay_merge_commit": "dc7f29fbd7e78fbdcdb9c90d1df515882528fdeb",
            "transport_normalization": "remove-exactly-one-terminal-lf",
            "legacy_rendered_bytes": len(legacy_render.encode("utf-8")),
            "legacy_rendered_sha256": hashlib.sha256(legacy_render.encode("utf-8")).hexdigest(),
            "public_bytes": len(public_body.encode("utf-8")),
            "public_sha256": hashlib.sha256(public_body.encode("utf-8")).hexdigest(),
            "public_body": public_body,
        }
        validate_activation_receipt(receipt, self.root)

        changed = copy.deepcopy(receipt)
        changed["public_body"] += " "
        with self.assertRaisesRegex(ValidationError, "normalized renderer output"):
            validate_activation_receipt(changed, self.root)

    def test_json_round_trip_does_not_change_world(self) -> None:
        encoded = json.dumps(self.state)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["world"], self.state["world"])
        self.assertEqual(word_count(decoded["world"]), self.state["world_word_count"])


if __name__ == "__main__":
    unittest.main()
