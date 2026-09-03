# Continuity ledger

**Status: active exactly when `canon/activations/chapter-zero-r000.json` is valid and reachable from `main`; the receipt preserves `861d5d7… / c35281`.**

The active ledger contains at most twelve compact rows. Detailed history remains in source states and comments. Removing a row requires an explicit `TRANSFORMED`, `RESOLVED`, or `DORMANT` delta.

| Id | Kind | Status after R002 | Durable fact | First source |
|---|---|---|---|---|
| `orra` | place/community | ACTIVE | The travelling city has failed to reach the sea for the first recorded time. | c35281 |
| `mara` | character | ACTIVE | Youngest mapmaker; tied the three named scraps to their citizens, stopped the bell with the ORRA scrap, then used salt water in a borrowed hand to reveal the walker's reflected route. | c35281, c35282, c35449, c37680 |
| `edda` | character | dormant seed | Keeper of the salt wells; no additional motive established yet. | region seed only |
| `rib-guild` | collective | ACTIVE | Digging toward the whale's heart; a sealed heartward tunnel on the walker's route lies beyond a door they have not opened. | c35281, c37680 |
| `glass-whale` | being/place | ACTIVE | Sleeping beneath Orra; one eye opens when the buried bell sounds. | c35281 |
| `western-bell` | object/mystery | ACTIVE | Rings beneath the western square; stopped mid-ring when the ORRA scrap covered the miniature's missing square. | c35281, c35449 |
| `unmarked-three` | collective/mystery | ACTIVE | Visible but absent from Mara's map; one involuntarily mirrored the ink walker and now bears a wet footprint that reveals its intended route when touched by water. | c35281, c35282, c36993, c37680 |
| `dry-orra-model` | object/place | ACTIVE | Drawn from a salt well; lacks the western square, and turning it separated the walker's shadow from its ink figure; a crossed doorway opens for one breath onto the impossible street. | c35406, c36993 |
| `orra-scrap` | object/mystery | ACTIVE | Fourth named scrap; its impossible street appears in salt water as a glass-rib bridge, where the reflected walker waits at the heartward threshold. | c35449, c37680 |
| `heartward-tunnel` | place/mystery | ACTIVE | A sealed tunnel toward the whale's heart; the footprint's first reflection identifies it as the walker's intended route. | c37680 |

## Ledger rules

- `ACTIVE`: needed for current causal play.
- `DORMANT`: absent from the active state but available by sourced callback.
- `TRANSFORMED`: identity or function changed; both old and new forms stay traceable.
- `RESOLVED`: its open conflict ended, while the historical fact remains true.

Only ids present in a canonical state's `ledger_delta` count toward the twelve-row active bound. A region seed may remain outside active canon until introduced by a valid move. A summary never overrides a source; conflicts must be repaired publicly.
