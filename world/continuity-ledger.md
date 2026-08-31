# Continuity ledger

**Status: launch candidate with provisional Chapter-Zero entries. Nothing here is active before Genesis activation.**

The active ledger contains at most twelve compact rows. Detailed history remains in source states and comments. Removing a row requires an explicit `TRANSFORMED`, `RESOLVED`, or `DORMANT` delta.

| Id | Kind | Status after Genesis | Durable fact | First source |
|---|---|---|---|---|
| `orra` | place/community | ACTIVE | The travelling city has failed to reach the sea for the first recorded time. | candidate Genesis |
| `mara` | character | ACTIVE | Youngest mapmaker; says the whale dreams tomorrow's streets. | candidate Genesis |
| `edda` | character | dormant seed | Keeper of the salt wells; no additional motive established yet. | region seed only |
| `rib-guild` | collective | ACTIVE | Digging toward the whale's heart. | candidate Genesis |
| `glass-whale` | being/place | ACTIVE | Sleeping beneath Orra; one eye opens when the buried bell sounds. | candidate Genesis |
| `western-bell` | object/mystery | ACTIVE | Rings beneath the western square; nobody remembers building it. | candidate Genesis |
| `unmarked-three` | collective/mystery | ACTIVE | Three visible citizens are absent from Mara's newest map. | candidate Genesis |

## Ledger rules

- `ACTIVE`: needed for current causal play.
- `DORMANT`: absent from the active state but available by sourced callback.
- `TRANSFORMED`: identity or function changed; both old and new forms stay traceable.
- `RESOLVED`: its open conflict ended, while the historical fact remains true.

Only ids present in a canonical state's `ledger_delta` count toward the twelve-row active bound. A region seed may remain outside active canon until introduced by a valid move. A summary never overrides a source; conflicts must be repaired publicly.
