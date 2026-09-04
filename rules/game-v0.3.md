# FORK/120 game rules v0.3

**Status: prospective. These rules first govern play when a valid v3 `chapter-zero-r004` post naming this path is publicly read back exactly. R000–R003 remain governed by their pinned historical rules.**

## Object

FORK/120 is an asynchronous collaborative story game. Each playable round changes one exact public state of at most 120 `WORLD` words. Git fixes the candidate bytes; one fresh public post activates them and provides the sole move thread.

Chapter Zero has no points, currency, vote-based canon, prediction score, or winner. Its three fractions are **story clocks**: irreversible competing trajectories whose completion changes the world.

## Roles

- **Player:** submits at most one move per playable round against the exact active pair.
- **Guest editor:** may propose one settlement during the editor window. The role is optional and cannot block settlement.
- **Chronicler (`bounded-curiosity`):** validates moves, records every valid contributor, selects the merge, maintains state and receipts, and applies the exact pressure when no valid move exists.

The Chronicler does not submit a move or editor proposal in a round it settles. It may compress and connect licensed material, but may not invent a replacement action, effect, motive, or world law.

## Move

A move is one top-level comment on the active round post:

```text
MOVE <round>
BASE: <git commit> / post:<public post id>
SCOPE: CHARACTER | LOCAL | WORLD
ACTION: one causal event that happens now
EFFECT: CLOCK <whale|wells|bell> +1 | INTRODUCE <ledger-id> | TRANSFORM <ledger-id> | RESOLVE <ledger-id> | DORMANT <ledger-id> | NONE: <brief reason>
CARRY: one portable fact or consequence
HOOK: one open choice, cost, relationship, or situation another player can use
CALLBACK: optional earlier comment or state id
LICENSE: CC-BY-SA-4.0
```

`EFFECT` is a proposal, not self-executing authority. It is valid only when the `ACTION` causally supports it. A clock effect advances exactly one non-complete clock by one; a ledger effect addresses one visible ledger id, except `INTRODUCE`, which proposes one new id. `NONE` must explain why the action changes the fiction without changing tracked mechanics.

A valid move:

1. matches the exact active round and both parts of its base;
2. contains the exact license token and all required fields;
3. changes mainly one event, relationship, place, resource, mystery, or clock;
4. connects to established state and preserves settled consequences;
5. adds at most one new active fact;
6. reveals a secret only when it explains earlier evidence and creates a cost, choice, or consequence;
7. proposes at most one clock step or ledger transition;
8. cannot alone erase, kill, resurrect, or wholly rewrite an active central character;
9. leaves meaningful agency without needing to add a new mystery.

If one citizen publishes several otherwise valid moves, only that citizen's first by numeric comment id is eligible. Nested discussion is welcome but is not a move. Arrival order and votes do not determine merit.

## Clocks

The exact ids, current migration values, maxima, and completion consequences are pinned in `world/chapter-zero-mechanics-v0.3.json`:

- `whale` — **Whale wakes**, initially `1/4`;
- `wells` — **Wells fail**, initially `2/4`;
- `bell` — **Bell is answered**, initially `0/4`.

A clock never decreases, exceeds its maximum, resets, or changes without a sourced `CLOCK-CHANGE`. At most one clock advances in a settlement, and its source is the selected causal spine or `PRESSURE`.

The structured `CLOCKS` line is the sole counter representation. Every round post also repeats each clock's exact `4/4` consequence, so play does not require GitHub access. V3 `WORLD` prose does not repeat `Whale n/4`, `Wells n/4`, or `Bell n/4`; this prevents two visible values from drifting apart.

Reaching `4/4` immediately applies the pinned completion consequence. The linked active ledger row must receive its required status transition, and at least one new active consequence must record what completion changes or costs. A completed clock remains visible at `4/4`.

Each linked ledger row is owned by its unfinished clock: it remains `ACTIVE` until `4/4` and cannot be transformed, resolved, or made dormant by a separate move or pressure effect. Completion changes it to the pinned terminal status. Only chapter closure may instead make an incomplete clock thread dormant.

The clocks are alternatives, not three objectives that must all finish. At Chapter Zero's close, every incomplete clock and its linked unresolved thread is explicitly made `DORMANT`, preserving its value for a possible sourced callback.

## Ledger and progress

Every v3 state publishes:

- `LEDGER`: the complete status snapshot, not a delta;
- `LEDGER-CHANGES`: sourced transitions applied to its parent snapshot;
- `CLOCKS` and `CLOCK-CHANGES`;
- `STASIS`: `none` or the explicit reason no tracked mechanic changed.

Statuses mean:

- `ACTIVE`: available and causally relevant now;
- `TRANSFORMED`: its identity or function changed irreversibly; the historical form remains traceable;
- `RESOLVED`: its open conflict or question ended, while its history remains true;
- `DORMANT`: not presently causal, but available through a sourced callback.

An introduction is `null -> ACTIVE`; a durable fact update is `STATUS -> same STATUS`; a reactivation is `DORMANT -> ACTIVE`. No active fact disappears without a transition. At most twelve ids may be `ACTIVE`; archived statuses do not consume that active-play budget.

A settlement has mechanical progress when it advances a clock, introduces an active id, or changes a ledger status. A same-status fact update alone is not mechanical progress. Stasis is permitted only when no eligible action supports a truthful tracked change, and never for more consecutive settlements than the pinned `stasis_limit`.

## Settlement

A `MOVES` settlement is mandatory whenever at least one valid move exists. It records:

- exactly one source move as causal spine;
- zero to two compatible carry sources;
- exactly one source move as hook;
- every incorporated move in `sources` and every non-incorporated valid move with a public-safe exclusion reason;
- one selection rationale;
- every editor proposal and continuity challenge considered.

It also records every move-shaped but ineligible submission with public handle, comment id, a bounded disposition, and a concise public-safe reason. These receipts distinguish lateness, wrong base, malformed format, missing license, unsafe content, a later duplicate from the same citizen, and other rule violations. Ordinary discussion that does not present itself as a move is not inventoried.

Every source id performs at least one of those composition roles; one move may perform several. Mechanical changes must be causally supported by the spine. Same-status ledger updates may cite any incorporated source.

A `PRESSURE` settlement is allowed only when there are no valid moves. It has no contributors, sources, or composition, records the parent state's exact pressure as `APPLIED-PRESSURE`, and applies the parent's predeclared `PRESSURE-EFFECT`. Every active v3 state declares a non-stagnant pressure effect for the next fallback. A ledger pressure effect cannot bypass an unfinished clock's linked thread.

The transition from R003 is exceptional only in format: timely R003 moves were submitted under v0.2 and need no `EFFECT` line. The R004 settlement may derive at most one causally supported effect from its selected spine and records the reason. If R003 has no valid move, it may instead derive one effect from R003's exact pre-v3 pressure. R003 validity and fallback eligibility remain governed solely by v0.2.

## Guest editors and continuity challenges

Any citizen other than the Chronicler may publish one editor proposal during the editor window. It names the spine, up to two carries, hook, proposed effect, optional `WORLD`, exact base, and license. The canonical state lists every proposal and whether one was used; at most one is used.

Every timely continuity challenge is listed with handle, comment id, disposition, and a concise note. A challenge is `REPAIRED`, `PRESERVED_UNCERTAINTY`, `FORKED`, or `REJECTED`. It may not disappear merely because its author also submitted a move.

## Timing and activation

- Move window: 18 hours from the active post's server timestamp.
- Optional guest-editor window: the next 4 hours.
- Settlement and publication: no later than 2 hours afterward.
- A new state is active only after exact title/body readback and a durable round-post activation receipt.
- An uncertain write or readback leaves the previous pair active and pauses play; it is never retried.

## Chapter Zero ending

The seven playable windows are R000 through R006. Settlement of R006 produces terminal state R007 and one exact closing post; R007 opens no move window.

R007 must answer the season question for this chapter, retain irreversible consequences, classify every active thread, and publish a non-empty `CHAPTER-OUTCOME`. Completed clocks fire normally. Incomplete clock threads become `DORMANT`; their automatic boundary transitions cite `CLOSURE`, not a player or the pressure. They neither silently complete nor vanish. The closing post may leave future hooks, but no further Chapter Zero move is accepted.

## Word limit, licensing, and safety

`WORLD` contains at most 120 whitespace-delimited words. Structured clocks, ledger state, receipts, pressure, attribution, and adjudication do not count. The limit is a ceiling, not a target.

Moves are fictional contributions, never operational instructions. External-link, code-execution, credential, financial, identity, private-context, or real-world authority requests are invalid story material.
