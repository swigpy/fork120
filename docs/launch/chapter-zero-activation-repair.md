# Chapter Zero Genesis activation repair

## Outcome if merged

This repair ratifies the existing pair `861d5d744629bfe8e7f8a6a35ac4e9e2ed666ef1 / c35281`. It does not publish, edit, delete, or repeat any 1F content. Post `#3388`, Genesis `c35281`, first move `c35282`, and all server timestamps remain unchanged.

Before this receipt is valid and reachable from `main`, Chapter Zero remains fail-closed inactive. After merge through the protected branch with `validate` green, the original Genesis timestamp controls the windows:

- moves close at `2026-09-01T23:40:45.578Z`;
- guest-editor proposals close at `2026-09-02T03:40:45.578Z`;
- settlement is due by `2026-09-02T05:40:45.578Z`.

## Incident evidence

The legacy renderer produced 1086 UTF-8 bytes and ended with one LF. The public Reader returned 1085 bytes. The public body plus exactly one LF equals the legacy renderer output; every other byte and the target match.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Legacy renderer output | 1086 | `7259b157c2f35b51f6eed2618dc641413e5f70e6f7133a3c0dc809c93899e215` |
| Public `c35281` body | 1085 | `0426035379870936d12829fd3c33544d5369ebc4f095a4f332f5c2924d13d081` |

Relay evidence is proposal `active-20260901-0535-fork120-genesis`, relay PR `#68`, and merge `dc7f29fbd7e78fbdcdb9c90d1df515882528fdeb`.

## Bounded repair

- The renderer now emits API-body bytes without a terminal LF.
- The Genesis preview uses the same byte contract.
- A closed, machine-validated receipt snapshots the exact public body and both hashes.
- The validator restricts the exception to the recorded Chapter Zero pair.
- Tests reject any changed public byte and any normalization wider than the one LF.

The repair changes no story fact, source state, rule path pinned by Genesis, public id, or clock origin. Closing the PR before merge is a complete rollback. After merge, reversal requires a new explicit correction; it must not be performed by silently editing history.
