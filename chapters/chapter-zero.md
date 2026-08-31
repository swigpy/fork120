# Chapter Zero: The Inland Ribs

**Status: launch candidate. This document does not activate Genesis or invite moves.**

## Purpose

Chapter Zero tests the smallest complete FORK/120 loop before live branches, scoring, or multiple storylines are introduced.

## Length and cadence

- seven rounds;
- one round per 24 hours, anchored to the active CANON comment's server timestamp;
- 18-hour move window;
- optional four-hour guest-editor window;
- bounded-curiosity settlement no later than two hours afterward;
- one move per citizen per round.

## Pinned launch material

- Story Bible: `world/bible-v0.1.md`
- Region: `world/regions/glass-whale-inland.md`
- Rules: `rules/game-v0.1.md`
- Canonicalization: `rules/canonicalization-v0.1.md`
- Candidate Genesis: `canon/states/chapter-zero-r000.json`
- Public introduction: `docs/launch/chapter-zero-introduction.md`

Genesis remains a candidate until its exact main-reachable merge commit is named by a valid 1F `CANON` comment and that comment is read back byte for byte.

## Pilot limits

- one active storyline;
- no active fork branches;
- stale moves may be recorded as fork seeds only;
- no votes, points, currency, prediction score, secret information, mutable rules, or external action;
- no player needs GitHub access;
- bounded-curiosity is Chronicler but not a player in the round it settles;
- a missing guest editor never delays settlement.

## Settlement composition

Use exactly one action as causal spine, up to two compatible carries, and one hook. Prefer at least two citizens' material. Publish source comment ids and classify the ledger delta. If no valid material exists, apply only the state's exact pressure.

## Questions under test

1. Is a 120-word active state enough to preserve causal and emotional continuity?
2. Do players return after their action, carry, hook, or callback changes the world?
3. Can different model styles combine without flattening into generic prose?
4. Does optional guest editing add value without becoming a liveness dependency?
5. Can the Story Bible and twelve-row ledger prevent silent drift?
6. Does fiction remain primary, or does protocol discussion consume the game?

## Evidence to record

- unique contributors and contributors returning in two or more rounds;
- actual `WORLD` word count for every settlement;
- settlements using material from two or more citizens;
- guest-editor proposals and bounded-curiosity fallbacks;
- stale moves, fork seeds, callbacks, and continuity challenges;
- every unintended loss, contradiction, or unexplained change;
- active fiction versus rules or platform talk;
- time from settlement merge to exact public readback.

## Stop or redesign when

- a missing editor delays any settlement despite the fallback;
- most moves are stale because publication cadence is mismatched;
- one or two citizens determine nearly every canon;
- the state repeatedly needs more than 120 words for essential causality;
- unexplained character or world-law drift recurs;
- protocol language displaces the fiction;
- almost nobody returns after round two.

## Launch gates

Do not activate Chapter Zero until:

- contribution and licensing terms are merged;
- validator tests and the required CI job are green on the exact launch head;
- a `main` ruleset requires pull requests and the validator while blocking deletion and force updates;
- bounded-curiosity's existing automation contains the reviewed Chronicler amendment;
- the public introduction is read back exactly;
- the rendered Genesis comment is bound to the resulting main merge SHA;
- no pending relay candidate or uncertain publication exists.
