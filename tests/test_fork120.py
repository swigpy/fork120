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
    render_canon,
    validate_activation_receipt,
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
        (self.root / "world" / "bible-v0.1.md").write_text("bible\n", encoding="utf-8")
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
