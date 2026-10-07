# Does commission ordering concentrate minipool exits?

I tested whether following RPIP-71's suggested commission priority wipes more node minipool books than random selection at the same expected ETH exit credit. **At this snapshot, it does under all four tie-breaks.**

Method, in three lines:

1. Block **26,127,238** (2026-10-05, 16:03:35 UTC): 11,571 eligible minipools / 1,323 node addresses; exclude already exiting or withdrawn validators.
2. Sort exact commission descending, then soonest sweep / latest sweep / random / validator index; take a priority prefix without exceeding the **58,538.368607-ETH cap** for a 50,000-rETH net shortfall.
3. Compare against 1,000 random draws; sweep uses 20 randomized index rotations. Seed **20261007**; rerun **20261008** and test including the first cap-crossing validator.

| Commission tie-break / baseline | Nodes touched | Eligible minipool books wiped | Exits on wiped nodes | Top-10 node share | RPL on wiped nodes |
|---|---:|---:|---:|---:|---:|
| Soonest sweep | 545.5 [493.7–598.0] | 235.1 [203.8–280.1] | 18.2 [12.1–24.3]% | 42.4 [40.5–44.7]% | 421,731 [235,383–752,199] |
| Latest sweep | 541.1 [489.6–587.6] | 250.8 [198.9–299.0] | 20.4 [12.1–28.6]% | 43.0 [41.5–46.1]% | 403,226 [240,755–718,190] |
| Random ties | 655.3 [638.0–672.0] | 222.4 [211.0–233.0] | 12.5 [11.8–13.2]% | 39.5 [38.9–40.1]% | 205,714 [168,150–239,139] |
| Validator index | 598.0 | 206.0 | 12.1% | 41.7% | 632,229 |
| Random baseline | 671.8 [648.0–694.0] | 117.6 [103.0–132.0] | 5.2 [4.5–6.0]% | 22.8 [21.7–24.0]% | 104,274 [61,375–138,826] |


Cells show mean [5th–95th percentile]; sweep ranges describe rotation sensitivity, not a timing forecast. “Wiped” means all **eligible minipools** selected; nodes may retain megapool validators or other minipools.

The key result is **206–251 wiped books across commission rules, versus 118 random [103–132]**. Soonest sweep touches **546 nodes versus 672** random, has **18.2% versus 5.2%** of exits on wiped nodes, a **42.4% versus 22.8%** top-10 share, and **422k versus 104k RPL** associated with wiped nodes. RPL is counted once per node and is exposure, not predicted selling.

The spreadsheet scenario reconciles; the wiped-book conclusion holds with another seed and the overshoot rule. Sweep point estimates move with the cursor. The 10k and 200k runs also wipe more books under every commission tie-break, but **top-10 share is not higher under every rule at 200k**. The baseline is matched on ETH, so different bonds mean different exit counts.

Script, full CSV, block, seeds, table, chart, spreadsheet and checks: [https://github.com/winverse2755/rocketpool-minipool-exit-simulation](https://github.com/winverse2755/rocketpool-minipool-exit-simulation).

Limitations: **draft RPIP; oDAO commission priority is a SHOULD and sweep tie-break a MAY; static snapshot; no behaviour modelled.** Scenario sizes are net shortfalls, not gross queue demand. Circular index order is a sweep proxy, not withdrawal time. No exit delays, operator responses, migration, cooldown history or RPL sales are modelled. The crossing sensitivity violates the draft hard cap and is not the recommended implementation. This tests the suggested ordering policy, not the isolated causal effect of commission clustering.

The broader ordering-and-timing comparison remains proposed funded work; this is the static minipool result.
