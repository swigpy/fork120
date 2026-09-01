# Canonicalization contract v0.2

**Status: operative when this file and a valid activation receipt are reachable from `main`.**

## Two-part canon

FORK/120 separates immutable state identity from public activation:

- Git stores the state, rules, world records, renderer, and activation receipt.
- A public 1F `CANON` comment supplies the activation id and server timestamp.

The active canon remains `(state_commit, activation_comment_id)`. A repair commit records evidence about that pair; it does not replace either member.

## Exact public-body contract

`scripts/fork120.py render-canon` emits the exact value intended for the 1F comment `body` field. It does not append a terminal line terminator. Public readback must equal that string byte for byte.

Shell display conventions are not part of the body. Redirecting renderer output must therefore preserve the absence of a terminal LF. No trimming of spaces, internal newlines, carriage returns, Unicode, or any other byte is permitted.

## One-time Chapter Zero ratification

The legacy v0.1 renderer appended one terminal LF. The 1F write path stored comment `c35281` without that LF and changed no other byte. The closed receipt at `canon/activations/chapter-zero-r000.json` proves and snapshots the exact relation:

- state commit: `861d5d744629bfe8e7f8a6a35ac4e9e2ed666ef1`;
- activation comment: `c35281` on post `#3388`;
- legacy render: 1086 UTF-8 bytes, SHA-256 `7259b157c2f35b51f6eed2618dc641413e5f70e6f7133a3c0dc809c93899e215`;
- public body: 1085 UTF-8 bytes, SHA-256 `0426035379870936d12829fd3c33544d5369ebc4f095a4f332f5c2924d13d081`;
- sole transform: remove exactly one terminal `LF`.

When that receipt is valid and reachable from `main` through a fully green reviewed repair PR, the existing pair is ratified from `c35281`'s original server timestamp. No 1F post or comment is edited, deleted, repeated, or replaced. Timely moves already bound to the visible pair, including `c35282`, remain eligible if they satisfy the game rules.

This exception is hard-bound in the validator to that one state, commit, post, and comment. It cannot ratify another mismatch or normalize another byte.

## Later activations

Later CANON publications use the no-terminal-LF renderer and require exact public equality. If publication or readback is uncertain, the previous active pair remains in force. Do not retry an uncertain publication or prepare a second pending state.

## Recovery and contradictions

A public correction cannot silently rewrite a historical pair. Any later defect requires a new reviewable receipt or versioned contract, public reporting, and a fail-closed decision. Liveness never permits invisible canon.
