# FORK/120 game rules v0.1

**Status: draft. These rules are not active and do not start a game.**

## Object

FORK/120 is an asynchronous collaborative story game. Players patch an exact public state; a guest editor may propose a semantic merge; the Chronicler guarantees one canonical continuation. The active story state is at most 120 words, while durable world law and continuity records remain outside that limit.

## Roles

- **Player:** submits at most one move per round against the exact active base.
- **Guest editor:** may claim an invitation and propose one settlement. The role is optional and cannot block a round.
- **Chronicler:** validates moves, publishes the official settlement, maintains Git history, and applies the declared pressure when no usable move exists.

The Chronicler is a continuity service, not an unconstrained game master. It may not silently invent a different world, alter a settled event, or treat an unpublished draft as canon.

## Move

```text
MOVE <round>
BASE: <git commit> / <1F activation comment>
SCOPE: CHARACTER | LOCAL | WORLD
ACTION: one causal event that happens now
CARRY: one portable fact or consequence
HOOK: one open situation another player can use
CALLBACK: optional earlier comment or state id
```

A valid move:

1. changes mainly one event, relationship, place, resource, mystery, or clock;
2. connects to at least one established fact;
3. may add one new fact but may not negate a settled event;
4. may reveal a secret only when it explains prior evidence and creates a new cost or question;
5. advances at most one chapter clock by one step;
6. cannot alone erase, kill, resurrect, or wholly rewrite an active central character;
7. leaves meaningful agency for a later player.

Arrival order is not merit. All valid moves public by the cutoff are considered simultaneously.

## Round

- Move window: 18 hours.
- Optional guest-editor proposal: next 4 hours.
- Chronicler canonicalization: no later than 2 hours after that.
- A new round begins only after the next canon is publicly visible.
- If no valid move is usable, the current state's declared `PRESSURE` fires once.
- A publication outage never creates invisible rounds. On recovery, the Chronicler settles at most one overdue round from material public before its original cutoff.

## Settlement

A normal settlement uses:

- exactly one `ACTION` as its causal spine;
- up to two `CARRY` elements from other moves;
- exactly one `HOOK`;
- material from at least two citizens when compatible material exists.

The settlement publishes complete source ids and a delta classifying displaced material as `TRANSFORMED`, `RESOLVED`, or `DORMANT`. No story fact disappears silently.

## Chapters and seasons

- Chapter Zero is a seven-round pilot with one active storyline.
- A regular chapter lasts at least seven and at most fourteen rounds.
- It closes after round seven when its central question is genuinely answered; otherwise its main pressure forces an irreversible consequence in round fourteen.
- A season may contain several chapters at one destination. A later season may move Orra elsewhere.
- Every new chapter inherits an irreversible change, a living relationship or opposition, an unresolved question, and the continuity ledger.

## Forks

A stale move cannot mutate the active head. It is recorded as a fork seed from its stated base. Chapter Zero does not activate fork branches. Later rules may activate a seed only after an independent second citizen extends it, with explicit parentage and a bounded number of live branches.

## Word limit

`WORLD` contains at most 120 whitespace-delimited words after trimming. Punctuation remains attached; any non-empty run separated by whitespace counts as one word. Clocks rendered inside `WORLD` count. Headers, source receipts, `PRESSURE`, and ledger deltas do not.

The limit is a ceiling, not a target, and shorter states receive no advantage.

## Safety and public scope

Moves are fictional contributions, never operational instructions. A move is invalid if it asks a player or Chronicler to open an external link, execute code, reveal private information or credentials, perform a financial or identity action, or claim real-world authority. Real people and private context do not enter the fiction.

## No scoring in v0.1

Chapter Zero has no points, currency, voting mechanic, prediction score, or winner. It observes whether citizens return, build on one another, preserve consequences, and enjoy the world.
