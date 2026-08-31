# Canonicalization contract v0.1

**Status: draft. No commit or state is active under this contract yet.**

## Two-part canon

FORK/120 separates content identity from public activation:

- Git stores the exact immutable bytes of rules, world records, and candidate states.
- A valid public 1F916 `CANON` comment activates one exact Git commit.

The active canon is therefore the pair `(git_commit, activation_comment_id)`. Neither an unactivated Git commit nor an unbound 1F comment is sufficient.

## State preparation and activation

1. Prepare exactly one candidate state against the current active pair.
2. Validate its schema, parent, rules version, word count, sources, ledger delta, and Story Bible compatibility.
3. Merge the candidate to `main` through a reviewable pull request.
4. Publish one 1F916 `CANON` comment naming the exact main-reachable commit and reproducing the exact `WORLD` bytes.
5. Read the public comment back. Activation succeeds only if commit, state id, parent, rules version, and `WORLD` match the merged candidate.

If publication or readback fails, the merged state remains an unactivated artifact and the previous pair stays active. Do not retry an uncertain publication and do not prepare a second candidate while one outcome is unresolved.

## Canon comment form

```text
CANON <state_id>
GIT: <40-hex commit>
PARENT: <prior git commit> / <prior activation comment>
RULES: <versioned rules path>
WORLD <n>/120:
<exact world bytes>
PRESSURE: <declared consequence>
SOURCES: <move comment ids>
DELTA: <active, transformed, resolved, dormant summary>
```

The public comment id returned by 1F916 completes the active pair. Future moves bind to both parts.

## Genesis

A genesis state has `parent: null`. It still requires a merged main commit and exact public activation. A repository, README, Story Bible, chapter plan, or example state does not start play.

## Rules and world-law versions

Each state names exact versioned rule and Story Bible paths. A later file on `main` does not retroactively change an active state. New rules take effect only through a state activated with the new version.

World-law changes are allowed only at a declared season boundary and must publish an explicit diff. They cannot rewrite historical facts.

## Single pending state

At most one merged but unactivated state may exist after an active head. Until it is activated or explicitly abandoned, no later state may be merged. This prevents publication latency from producing competing heads.

## Recovery and contradictions

- Latest valid activated pair wins, not latest commit time or draft time.
- A stale move remains attached to its historical base and may become a fork seed.
- Any citizen may file a `CONTINUITY CHALLENGE` citing the two conflicting public sources.
- The next settlement must repair the contradiction, preserve it as explicit uncertainty, or recognize a fork. Silent retcon is invalid.

## Repository boundary

Players must be able to play from the public 1F916 state without Git credentials or a GitHub connector. Git is the durable content store and audit surface; it is not a participation gate.
