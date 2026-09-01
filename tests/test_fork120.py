# SPDX-License-Identifier: MIT

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.fork120 import ValidationError, render_canon, validate_state, word_count


class Fork120ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "rules").mkdir()
        (self.root / "world").mkdir()
        (self.root / "rules" / "game-v0.1.md").write_text("rules\n", encoding="utf-8")
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
        self.assertTrue(rendered.endswith("DORMANT=none\n"))

    def test_json_round_trip_does_not_change_world(self) -> None:
        encoded = json.dumps(self.state)
        decoded = json.loads(encoded)
        self.assertEqual(decoded["world"], self.state["world"])
        self.assertEqual(word_count(decoded["world"]), self.state["world_word_count"])


if __name__ == "__main__":
    unittest.main()
