# Continuity ledger

**Status: R003 reference ledger. The exact active pair is preserved by `canon/activations/chapter-zero-r003.json`; v3 states become the machine-readable authority prospectively from R004.**

The active ledger contains at most twelve compact rows. Detailed history remains in source states and comments. Removing a row requires an explicit `TRANSFORMED`, `RESOLVED`, or `DORMANT` delta.

| Id | Kind | Status after R003 | Durable fact | First source |
|---|---|---|---|---|
| `orra` | place/community | ACTIVE | The travelling city has failed to reach the sea for the first recorded time. | c35281 |
| `salt-wells` | resource/threat | ACTIVE | Salt fills every well although the sea lies beyond the mountains; the Wells clock already stands at 2/4. | c35281 |
| `mara` | character | ACTIVE | Youngest mapmaker; used salt water and the ORRA scrap to reveal a streetless room inside a hollow whale rib and the older matching footprint across the bridge. | c35281, c35282, c35449, c37680, c38891, c38913, c38916 |
| `edda` | character | dormant seed | Keeper of the salt wells; no additional motive established yet. | region seed only |
| `rib-guild` | collective | ACTIVE | Digging toward the whale's heart; a sealed heartward tunnel on the walker's route lies beyond a door they have not opened. | c35281, c37680 |
| `glass-whale` | being/place | ACTIVE | Sleeping beneath Orra; one eye opens when the buried bell sounds, and a hollow rib contains a streetless room. | c35281, c38891, c38913 |
| `western-bell` | object/mystery | ACTIVE | Rings beneath the western square; stopped mid-ring when the ORRA scrap covered the miniature's missing square. | c35281, c35449 |
| `unmarked-three` | collective/mystery | ACTIVE | Visible but absent from Mara's map; one bears a wet footprint, and reverse-drawn salt exposed an older matching footprint on the bridge, showing something crossed outward. | c35281, c35282, c36993, c37680, c38916 |
| `dry-orra-model` | object/place | ACTIVE | Drawn from a salt well; reveals doors inside the whale even where no street leads, including a rib-door into the streetless room. | c35406, c36993, c38891, c38913 |
| `orra-scrap` | object/mystery | ACTIVE | Fourth named scrap; laid across the model's rib-door, it drinks salt and reveals the streetless room through its uncut edge. | c35449, c37680, c38913 |
| `heartward-tunnel` | place/mystery | ACTIVE | A sealed tunnel toward the whale's heart; the footprint's first reflection identifies it as the walker's intended route. | c37680 |
| `streetless-room` | place/mystery | ACTIVE | A hollow room inside a whale rib with no entering street; its door requires a second mark made from inside. | c38913 |

## Ledger rules

- `ACTIVE`: needed for current causal play.
- `DORMANT`: absent from the active state but available by sourced callback.
- `TRANSFORMED`: identity or function changed; both old and new forms stay traceable.
- `RESOLVED`: its open conflict ended, while the historical fact remains true.

Through R003, `ledger_delta` recorded the rows touched by that settlement and did not provide a reliable complete snapshot. The v0.3 migration baseline therefore consolidates every established active row above, including `salt-wells`; this is a tracking correction, not new fiction.

From the first valid v3 state, `ledger_state` is the complete status snapshot, `ledger_changes` is the sourced change set, and only `ACTIVE` rows count toward the twelve-row play budget. A region seed may remain outside active canon until introduced by a valid move. A summary never overrides a source; conflicts must be repaired publicly.
