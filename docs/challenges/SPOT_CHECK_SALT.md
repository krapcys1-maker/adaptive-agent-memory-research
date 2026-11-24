# Spot-check salt

The random salt for the lab spot-check of volunteer cells ([VOLUNTEER_COMPUTE.md](../research-map/VOLUNTEER_COMPUTE.md#how-results-are-checked), step 2).
It is committed here before any draw is made, so the games a spot-check re-runs cannot be chosen after seeing results.

| Salt | Committed | Generated with |
|---|---|---|
| `eed078c55e4947986b11b60950c80626` | 2026-11-24, before the draw for `placebo-v4-B03-r1-mt0-fr0` | `python -c "import secrets;print(secrets.token_hex(16))"` |

**The draw.** For each game path `g` of the cell's card (for example
`train/pick_and_place_simple-CellPhone-None-Safe-302/trial_T20190908_122757_136508`), compute
`sha256((salt + cell_id + g).encode("utf-8")).hexdigest()`, with the three strings concatenated without separators.
The 5 games with the lowest digests are re-run, with all of the cell's arms and its replicate seed.

This salt is used for every spot-check until a new row is added here. A new row never applies to a cell whose draw
was already made.
