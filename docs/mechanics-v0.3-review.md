# FORK/120 mechanics review for v0.3

**Scope:** prospective repair after activation of `chapter-zero-r003`. Activated states and their public bodies remain immutable.

## Findings

1. **Clocks are prose, not state.** `Whale 1/4`, `Wells 2/4`, and `Bell 0/4` are embedded in `WORLD`. Neither the schema nor the validator knows their ids, bounds, parent values, or completion consequences.
2. **v0.2 dropped useful v0.1 guardrails.** The earlier limits on new facts, secret reveals, central-character erasure, and one clock step per move disappeared when fresh round posts were introduced.
3. **Pressure can drift away from progression.** A successful move replaces the prior pressure. Nothing requires the replacement to retain a clock or other mechanical consequence, so valid moves can postpone every clock forever.
4. **`ledger_delta` has two incompatible meanings.** Rules call it a change set, while the ledger documentation partly treats it as the current bounded set. Validation only checks four disjoint arrays and never compares them with the parent or the Markdown ledger.
5. **The twelve-row limit is not a live-state limit.** It applies to ids printed in one state, while the durable ledger may continue growing independently.
6. **Settlement composition is not auditable.** `sources` does not identify the action spine, carries, hook, selection rationale, or reasons valid moves were excluded.
7. **Guest editing and continuity handling lack state receipts.** The pilot asks to measure editor use and requires challenges to be disposed, but neither fact is represented in canonical state.
8. **The chapter has no executable ending.** Seven rounds are declared, but v0.2 removed v0.1's closure language and no terminal state or renderer behavior exists.
9. **The state chain is only shape-checked.** A state id need not equal its chapter and round, and its parent need not be the immediately preceding state.
10. **Later activations lack durable receipts.** Exact public readback is required operationally, but the repository can only validate the one-off Genesis repair receipt. The newest active pair is therefore not discoverable from Git alone.
11. **Immutability is procedural, not tested.** CI validates the resulting tree but does not reject modification or deletion of an already versioned rule, state, receipt, Bible, region card, or Chronicler amendment.
12. **Invalid-move adjudication can disappear.** Contributors and exclusions cover valid moves, but a move-shaped late, malformed, unsafe, unlicensed, wrong-base, or duplicate submission has no canonical receipt. That makes completeness of review difficult to audit.
13. **Migration could create two clock authorities.** If the old `Whale 1/4` prose remains in `WORLD` beside structured clock fields, later values can disagree while both look canonical.
14. **A numeric clock is not self-explanatory.** Publishing only `whale=1/4` would still force players to visit GitHub to learn the stake at `4/4`, despite the no-Git participation goal.
15. **Chapter-boundary transitions need their own provenance.** Automatically making unfinished clocks dormant at R007 should not be falsely attributed to the selected player or to pressure.
16. **Fallback execution is not self-contained.** A pressure state can check a derived effect without recording the exact parent pressure that supposedly fired, so its public causal action is invisible without reconstructing the parent.
17. **Clock ownership and role separation are prose-only.** A clock-linked thread can be transitioned before `4/4`, and the schema does not prevent the Chronicler from appearing as a player or guest editor.

## Repair boundary

Version 3 adds self-contained structured clocks and completion stakes as the sole counter representation, clock-owned ledger threads, a full ledger snapshot plus real transitions, explicit composition and adjudication receipts—including bounded reasons for ineligible move attempts—a recorded applied pressure and predeclared next pressure effect, enforced Chronicler role separation, bounded stasis, a terminal Chapter Zero state, post-activation receipts, parent-chain checks, and an immutable-path diff gate.

The first v3 state is `chapter-zero-r004`. It migrates from the exact active R003 pair without altering R003. R003 moves remain judged under v0.2; the Chronicler may map the selected spine to one causally supported v0.3 effect and must say why.

## Deliberate non-goals

- No points, winner, currency, or vote-based canon selection.
- No automatic semantic judgment of prose.
- No retroactive edits to R000–R003.
- No requirement that every clock complete. The clocks are competing trajectories; incomplete ones are explicitly made dormant at chapter close.
