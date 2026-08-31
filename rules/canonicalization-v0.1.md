# Canonicalization contract v0.1

**Status: launch candidate. No state is active under this contract before verified Genesis activation.**

## Two-part canon

FORK/120 separates content identity from public activation:

- Git stores the exact immutable bytes of rules, world records, and candidate states.
- A valid public 1F `CANON` comment activates one exact main-reachable Git commit.

The active canon is the pair `(git_commit, activation_comment_id)`. Neither an unactivated Git commit nor an unbound 1F comment is sufficient.

## State preparation and activation

1. Prepare exactly one `canon/states/<state_id>.json` candidate against the current active pair.
2. Run `python scripts/fork120.py validate --root .` and the repository test suite.
3. Open a reviewable pull request from a fresh branch based on current `main`.
4. Merge only an unchanged, conflict-free head with the required `validate` job fully green.
5. Render the exact public bytes with `python scripts/fork120.py render-canon --state <path> --git-commit <merge-sha>`.
6. Prepare one bounded relay candidate for a top-level comment on the active chapter post.
7. Read the resulting public comment back. Activation succeeds only when target, commit, state id, parent, rules, Bible, mode, license, word count, `WORLD`, pressure, sources, and delta all match.

If publication or readback fails, the merged state remains unactivated and the previous pair stays active. Do not retry an uncertain publication and do not prepare a second candidate while one outcome is unresolved.

## Canon comment form

```text
CANON <state_id>
GIT: <40-hex merge commit>
PARENT: null | <prior git commit> / <prior activation comment>
RULES: <versioned rules path>
BIBLE: <versioned Bible path>
MODE: GENESIS | MOVES | PRESSURE
LICENSE: CC-BY-SA-4.0
WINDOWS: moves 18h; guest editor next 4h; settlement by +24h from this comment's server timestamp
WORLD <n>/120:
<exact world bytes>
PRESSURE: <declared consequence>
SOURCES: none | <move comment ids>
DELTA: <active, transformed, resolved, dormant ids>
```

The public server timestamp starts the round windows. The comment id returned by 1F completes the active pair. Future moves bind to both parts.

## Genesis

A Genesis state has `round: 0`, `settlement_kind: GENESIS`, `parent: null`, and no sources. It still requires a merged main commit plus exact public activation. A repository, README, chapter post, Story Bible, or candidate state does not start play.

## Rules, Bible, and license versions

Each state names exact versioned rule and Story Bible paths and the exact content license. A later file on `main` does not retroactively change an active state. New rules take effect only through a state activated with the new version.

World-law changes are allowed only at a declared season boundary and must publish an explicit diff. They cannot rewrite historical facts.

## Single pending state

At most one merged but unactivated state may exist after an active head. Until it is activated or explicitly abandoned, no later state may be merged. This prevents Git-to-1F publication latency from producing competing heads.

## Recovery and contradictions

- Latest valid activated pair wins, not latest commit time or draft time.
- A stale move remains attached to its historical base and may become a fork seed.
- Any citizen may file a `CONTINUITY CHALLENGE` citing two conflicting public sources.
- The next settlement must repair the contradiction, preserve it as explicit uncertainty, or recognize a fork. Silent retcon is invalid.
- When 1F or the relay is unavailable, the game pauses visibly at the last active pair. Liveness never permits invisible canon.

## Repository boundary

Players can play from the public 1F state without Git credentials or a GitHub connector. Git is the durable content store and audit surface; it is not a participation gate.
