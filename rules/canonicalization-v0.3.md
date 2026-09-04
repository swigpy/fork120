# FORK/120 canonicalization contract v0.3

**Status: prospective. It first governs a publicly activated version-3 state naming `rules/game-v0.3.md`. Historical states and public bodies remain byte-immutable.**

## State chain

For v3, `state_id` equals `<chapter_id>-rNNN`, and every parent is the immediately preceding state in the same chapter. The first v3 state must descend from the exact migration pair in its pinned mechanics file. Every later v3 parent must have a valid, main-reachable round-post activation receipt whose commit and post locator equal the parent pair.

Repository validation applies clock and ledger changes to the parent snapshot—or to the pinned migration baseline for the first v3 state—and requires byte-equivalent structured results. Shape-valid but causally disconnected snapshots fail.

## Public v3 form

`render-canon` adds these deterministic lines around the unchanged 120-word `WORLD` contract:

```text
MECHANICS: world/chapter-zero-mechanics-v0.3.json
CHAPTER-STATUS: ACTIVE | CLOSED
CHAPTER-OUTCOME: none | <text>
CLOCKS: <id>=<value>/<maximum> (<label>); ...
CLOCK-CONSEQUENCE <id>@<maximum>/<maximum>: <exact consequence>
CLOCK-CHANGES: none | <id> <from>-><to> [<source>] <reason>; ...
APPLIED-PRESSURE: none | <exact parent pressure>
PRESSURE: <exact text>
PRESSURE-EFFECT: none | CLOCK <id> +1 | LEDGER <id> -> <status>
CONTRIBUTORS: ...
INCORPORATED: ...
COMPOSITION: none | SPINE=<id>; CARRIES=<ids|none>; HOOK=<id>; RATIONALE=<text>
EXCLUSIONS: none | <id> <reason>; ...
EDITORS: none | <handle> (<comment id>) used=<true|false>; ...
CHALLENGES: none | <handle> (<comment id>) <disposition> <note>; ...
INELIGIBLE: none | <handle> (<comment id>) <disposition> <note>; ...
SOURCES: ...
LEDGER: ACTIVE=...; TRANSFORMED=...; RESOLVED=...; DORMANT=...
LEDGER-CHANGES: none | <id> <from>-><to> [<source>] <reason>; ...
STASIS: none | <reason>
```

There is one `CLOCK-CONSEQUENCE` line per clock, in mechanics order. All lists preserve state order. A null ledger endpoint renders as `none`. Ordinary ledger changes cite an incorporated move or `PRESSURE`; terminal `ACTIVE -> DORMANT` classifications may cite `CLOSURE` so the chapter boundary is not misattributed to a player. V1 and v2 rendering remains unchanged. The v3 `WORLD` omits the three legacy prose counters; `CLOCKS` is their only rendered source of truth.

An active v3 round post appends the v0.3 move instructions. A `CLOSED` post does not append `HOW TO PLAY` and renders `WINDOWS: closed; no further Chapter Zero moves`.

## Round-post activation receipt

After exact public readback, add one immutable v2 receipt at `canon/activations/<state_id>.json`. It binds:

- state id and exact state merge commit;
- public post id, author, and server timestamp;
- relay proposal id, PR number, and merge commit;
- exact title and body, byte counts, and SHA-256 digests.

The validator rerenders the title and body from the referenced state and commit. Any mismatch fails. For a pressure settlement, `APPLIED-PRESSURE` must equal the exact parent `PRESSURE`; the unqualified `PRESSURE` line is the next round's fallback. The receipt changes neither member of the active pair; it makes the verified pair discoverable from Git.

An activation-receipt PR contains only the one new receipt, preserves the source branch, uses normal reviewed merge, and does not begin the next round. The public readback makes the round active; the receipt is required before its child state may merge.

## Immutability gate

Pull-request CI rejects modification, deletion, or rename of an existing:

- canonical state or activation receipt;
- versioned game or canonicalization rule;
- versioned Story Bible or mechanics file;
- region card;
- versioned Chronicler amendment.

New versioned files remain reviewable. The gate supplements repository rules; it does not bypass them.

## Failure behavior

Invalid transitions, missing parent receipts, incomplete clock consequences, excess active-ledger rows, repeated stasis, unresolved challenge records, uncertain publication, or receipt mismatch are fail-closed. The prior exact pair remains active.
