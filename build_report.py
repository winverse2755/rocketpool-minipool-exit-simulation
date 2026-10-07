"""Build the results report and public post from the simulation outputs."""
import json
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT=Path(__file__).resolve().parent
PUBLIC='https://github.com/winverse2755/rocketpool-minipool-exit-simulation'


def main():
    meta=json.loads((ROOT/'results.json').read_text())
    sanity=json.loads((ROOT/'sanity.json').read_text())
    summary=pd.read_csv(ROOT/'summary.csv')
    seed, alternate=meta['seeds']
    def value(method,metric,demand=50000,seed_value=seed,rule='strict_cap'):
        return summary[(summary.seed==seed_value)&(summary.demand_reth==demand)&(summary.overshoot_rule==rule)&(summary.method==method)&(summary.metric==metric)].iloc[0]
    def mean(method,metric,**kwargs):
        return value(method,metric,**kwargs)['mean']
    table=(ROOT/'table.md').read_text()
    rate=Decimal(meta['rate_wei'])/10**18
    secondary=[]
    for d in [10000,200000]:
        if d not in meta['demands']:
            continue
        b=value('Random baseline','nodes_wiped',demand=d)
        methods=', '.join(f'{m.lower()} {mean(m,"nodes_wiped",demand=d):,.1f}' for m in ['Soonest sweep','Latest sweep','Random ties','Validator index'])
        secondary.append(f'- **{d:,} rETH:** wiped eligible books: {methods}; random {b["mean"]:,.1f} [{b.p05:,.1f}–{b.p95:,.1f}].')
    full_counts=', '.join(f'{m.lower()} {mean(m,"conservative_full_nodes_wiped"):,.1f}' for m in ['Soonest sweep','Latest sweep','Random ties','Validator index'])
    second_counts=', '.join(f'{m.lower()} {mean(m,"nodes_wiped",seed_value=alternate):,.1f}' for m in ['Soonest sweep','Latest sweep','Random ties','Validator index'])
    note=f'''# Does commission ordering concentrate Rocket Pool minipool exits?

**Yes in this static 50,000-rETH net-shortfall scenario.** All four commission tie-breaks wipe more eligible minipool books than the all-random baseline: means of 235.1 (soonest sweep), 250.8 (latest sweep), 222.4 (random ties), and 206 (validator index), versus 117.6 random [103–132]. The direction holds under a second seed and the tested overshoot rule. This does not establish that one sweep tie-break is consistently better than another, nor that the top-10 share increases at every withdrawal size.

## Method in three lines

1. Use the audited block **26,127,238** snapshot (5 October 2026, 16:03:35 UTC): **11,571 eligible minipools, 1,323 nodes**, at **{rate} ETH/rETH**; exclude exiting, withdrawn and slashed validators.
2. Sort exact commissions descending; tie-break by soonest sweep, latest sweep, random, or validator index. Select the largest priority prefix whose `sum(32 − bond)` is at/below net shortfall ETH minus 120 ETH, with no skipping.
3. Compare with **1,000 uniform random orderings without replacement**, also at matched ETH caps; random ties have 1,000 draws, sweep rules use **20 randomized candidate-index rotations**. Seed **{seed}**, repeat **{alternate}**; test strict cap versus including the first crossing validator.

## The table and chart

Cells are mean [empirical 5th–95th percentile], except validator index is fixed. Sweep intervals describe sensitivity across 20 positions; random intervals describe variability across 1,000 draws. Neither is a confidence interval for an estimated mean or a forecast probability of future outcomes. Percentile interpolation can produce fractional node counts.

{table}

![Nodes losing all eligible minipools under each commission tie-break against the all-random band](nodes_wiped.png)

**Definition of wiped:** every *eligible minipool* on that node is selected. These counts include single-minipool nodes. They do not imply that every validator run by the operator disappears. “Exits on wiped nodes” is selected validator count on these nodes divided by total selected validators. “Top-10” ranks node addresses by their selected validator counts, not their pre-existing sizes or credited ETH. RPL is total staked RPL in tokens, counted once per wiped node; it measures associated exposure, not slashing, unstaking, or selling.

Conservative full-node proxy: require all contract-staking minipools to be selected, and zero contract active megapool count. The 50k means are **{full_counts}**, versus **{mean('Random baseline','conservative_full_nodes_wiped'):,.1f}** random. This count also increases for every rule. Contract active megapool counts can include queued/exiting validators, and the dataset cannot rule out validators run outside Rocket Pool or common ownership across addresses.

The 50k cap is **58,538.36860736054925 ETH**. Commission rules select means of about **2,995–3,026 validators**, versus a random mean of **2,597.9**, because their higher-commission minipools have more 16-ETH bonds and hence less user capital per exit. This is a matched **ETH**, not matched validator-count comparison; it tests the ordering policy as a whole, not commission clustering in isolation. The existing static commission clustering result (72.28% of multi-minipool nodes uniform versus 18.91% shuffled) supplies context but does not isolate a causal contribution here.

## Phase 5: spreadsheet, seed, and overshoot checks

The validator-index scenario was independently reconstructed using Python `Decimal` and `Counter`, then written as ordinary spreadsheet formulas in [hand_check.xlsx](hand_check.xlsx). Spreadsheet status: **{sanity['spreadsheet_status']}**. [verification.json](verification.json) records the formula results. Application-recalculated output is [hand_check_recalculated.xlsx](hand_check_recalculated.xlsx), where present. The original workbook retains exact fee wei as text; the simulation uses exact wei, while the spreadsheet works in floating ETH. Boundary margins are large enough that spreadsheet precision does not decide the last selection.

The explicit arithmetic is **1,326 × 24 ETH + 1,669 × 16 ETH = 58,528 ETH**, across **2,995** validators. All commissions above 14% supply **1,655 exits / 26,480 ETH**; the selected 14% prefix supplies **1,340 exits / 32,048 ETH**. There are **598 touched nodes, 206 wiped books, 12.1202% of exits on wiped nodes, 41.7028% top-10 share, and 632,229.3958 RPL on wiped nodes**. Unused cap: **10.36860736054925 ETH**; the next validator credits 24 ETH and would exceed the cap by **13.63139263945075 ETH**. Selecting a later smaller row instead would break the requested prefix rule.

The second seed gives **{second_counts}**, against random **{mean('Random baseline','nodes_wiped',seed_value=alternate):.3f}** [{value('Random baseline','nodes_wiped',seed_value=alternate).p05:g}–{value('Random baseline','nodes_wiped',seed_value=alternate).p95:g}]. The sweep means move materially, especially soonest (235.1 → 209.8); the conclusion versus random persists, while the point estimate should not be treated as stable.

The overshoot sensitivity includes exactly the first cap-crossing validator. It is **not compliant with the draft hard cap** and is included only as a robustness test. Paired results add at most one exit and change the wiped count by at most one node per draw. The sign of each method-minus-baseline mean remains unchanged across both seeds and both overshoot rules, for all three sizes and the nine audited metrics. Machine-readable comparisons: [robustness.csv](robustness.csv), [overshoot_deltas.csv](overshoot_deltas.csv), [sanity.json](sanity.json). A single extra exit can wipe a large node's remaining book, so share/RPL changes need not be tiny.

## Additional sizes

Time permitted both additional runs, with the same 1,000-draw baselines and sanity checks.

{chr(10).join(secondary)}

At **200k**, top-10 concentration is not uniformly higher: random ties give **21.85%**, validator index **22.22%**, and random **22.68%**; soonest/latest give **23.03%/22.85%**. Thus “more minipool books wiped” holds here, while “higher top-10 share at every size” does not. At 10k the selected prefix ends at 15% commission; at 50k it reaches 14%, and at 200k it reaches 5%.

## Scope and limitations

- [RPIP-71](https://rpips.rocketpool.net/RPIPs/RPIP-71) is a **draft**; commission priority is an oDAO **SHOULD**, and the sweep tie-break is optional (**MAY**), not an enforced deterministic selection algorithm. [RPIP-80](https://rpips.rocketpool.net/RPIPs/RPIP-80) is in review and defines expected user capital as `32 ETH − bond`. Specifications may change; source text is saved in [sources](sources).
- This is a **static snapshot**, with **no behaviour modelled**: no operator responses, migration, new validators, delegates refusing exits, RPL selling, liquidity flows, exit queues, payout delays, or reentry. RPL exposure is not a forecast of market sales.
- Scenario sizes represent **net shortfalls expressed in rETH**, not gross queue deposits. Existing requested/voluntary exits and available ETH are assumed already netted out; no additional liquidity is deducted by this simulation. A 50k gross queue can require fewer exits.
- Sweep is circular order of eligible validator indices. Pointers are uniformly sampled starting candidates, not uniform all-Ethereum cursor positions or seconds until withdrawal. Soonest orders indices ascending from the cursor; latest reverses that circular order. Index clustering can add concentration; no timing benefit is inferred.
- This models a first request without historic penalties or cooldowns. RPIP-71's `did_not_exit_cooldown` reference remains absent from RPIP-80, which specifies increasing re-request windows instead. Eligibility does not certify future response to a request.
- Node addresses are the unit of analysis, not verified independent human operators. “Wiped” is scoped to eligible minipools; surviving megapool validators and already exiting/withdrawn minipools are tracked separately where the snapshot allows it.

## Reproduce and inspect

Use Python 3.12 or newer, install [requirements.txt](requirements.txt), and run from this directory:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python simulate.py
.venv/bin/python verify.py
.venv/bin/python build_report.py
```

The script needs **no RPC, API key, or live network access**. [minipools.csv](minipools.csv), [nodes.csv](nodes.csv), and [snapshot.json](snapshot.json) are copied byte-for-byte from the audited Phases 1–3 inputs. [provenance.md](provenance.md) records upstream collection and hashes. [sha256_manifest.json](sha256_manifest.json) checks all published artifact bytes.

To recalculate the spreadsheet independently on macOS, run the following before `verify.py` and `build_report.py` (Numbers may require OS automation permission):

```sh
osascript recalculate.applescript "$PWD/hand_check.xlsx" "$PWD/hand_check_recalculated.xlsx"
```

Other spreadsheet applications can recalculate the workbook directly. `verify.py` verifies an application-exported workbook when present. Merely reading the original workbook's cached values is not independent spreadsheet verification.

All per-draw results: [draws.csv](draws.csv). Aggregated 5th–95th percentiles: [summary.csv](summary.csv). Seeds and exact caps: [results.json](results.json). Pointers: [sweep_pointers.csv](sweep_pointers.csv). Representative 50k prefixes (including the first excluded row): [representative_prefixes.csv](representative_prefixes.csv). Per-node accounting: [representative_nodes.csv](representative_nodes.csv). Single chart is also available as [PDF](nodes_wiped.pdf) and [SVG](nodes_wiped.svg).

Public repository: [{PUBLIC}]({PUBLIC}). A shorter result post is [POST.md](POST.md).
'''
    (ROOT/'README.md').write_text(note)
    post=f'''# Does commission ordering concentrate minipool exits?

I tested whether following RPIP-71's suggested commission priority wipes more node minipool books than random selection at the same expected ETH exit credit. **At this snapshot, it does under all four tie-breaks.**

Method, in three lines:

1. Block **26,127,238** (2026-10-05, 16:03:35 UTC): 11,571 eligible minipools / 1,323 node addresses; exclude already exiting or withdrawn validators.
2. Sort exact commission descending, then soonest sweep / latest sweep / random / validator index; take a priority prefix without exceeding the **58,538.368607-ETH cap** for a 50,000-rETH net shortfall.
3. Compare against 1,000 random draws; sweep uses 20 randomized index rotations. Seed **{seed}**; rerun **{alternate}** and test including the first cap-crossing validator.

{table}

Cells show mean [5th–95th percentile]; sweep ranges describe rotation sensitivity, not a timing forecast. “Wiped” means all **eligible minipools** selected; nodes may retain megapool validators or other minipools.

The key result is **206–251 wiped books across commission rules, versus 118 random [103–132]**. Soonest sweep touches **546 nodes versus 672** random, has **18.2% versus 5.2%** of exits on wiped nodes, a **42.4% versus 22.8%** top-10 share, and **422k versus 104k RPL** associated with wiped nodes. RPL is counted once per node and is exposure, not predicted selling.

The spreadsheet scenario reconciles; the wiped-book conclusion holds with another seed and the overshoot rule. Sweep point estimates move with the cursor. The 10k and 200k runs also wipe more books under every commission tie-break, but **top-10 share is not higher under every rule at 200k**. The baseline is matched on ETH, so different bonds mean different exit counts.

Script, full CSV, block, seeds, table, chart, spreadsheet and checks: [{PUBLIC}]({PUBLIC}).

Limitations: **draft RPIP; oDAO commission priority is a SHOULD and sweep tie-break a MAY; static snapshot; no behaviour modelled.** Scenario sizes are net shortfalls, not gross queue demand. Circular index order is a sweep proxy, not withdrawal time. No exit delays, operator responses, migration, cooldown history or RPL sales are modelled. The crossing sensitivity violates the draft hard cap and is not the recommended implementation. This tests the suggested ordering policy, not the isolated causal effect of commission clustering.

The broader ordering-and-timing comparison remains proposed funded work; this is the static minipool result.
'''
    (ROOT/'POST.md').write_text(post)


if __name__=='__main__':
    main()
