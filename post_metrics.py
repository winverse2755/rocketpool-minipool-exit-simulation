"""Derive post metrics by replaying saved 50k orders; no new selection models.

Run after simulate.py. Checks every replay against the saved per-draw metrics.
Reward calculations use static user capital and contract commission, assuming
equal gross reward rate per staked ETH; they are not realised protocol APR.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from simulate import ROOT, METHODS, Simulation, WEI, prefix_length


def main():
    s=Simulation()
    meta=json.loads((ROOT/'results.json').read_text())
    seed=meta['seeds'][0]
    saved=pd.read_csv(ROOT/'draws.csv')
    saved=saved[(saved.seed==seed)&(saved.demand_reth==50000)&(saved.overshoot_rule=='strict_cap')].set_index(['method','draw'])
    pointers=pd.read_csv(ROOT/'sweep_pointers.csv')
    pointers=pointers[pointers.seed==seed].sort_values('draw')
    multi=s.sizes>1
    fees=s.fees/WEI
    capital=float(s.credits.sum())
    fee_capital=float(np.dot(s.credits,fees))
    rows=[]
    node_rows=[]

    def record(method,draw,order):
        k=prefix_length(np.cumsum(s.credits[order]),s.cap(50000),'strict_cap')
        chosen=order[:k]
        original=s.metrics(chosen,s.cap(50000))
        for key,value in original.items():
            assert np.isclose(value,saved.loc[(method,draw),key],rtol=1e-12,atol=1e-8),(method,draw,key)
        counts=s.counts(chosen)
        removed=counts/s.sizes
        touched=counts>0
        wiped=(counts==s.sizes)&touched
        credit=int(s.credits[chosen].sum())
        selected_fee_capital=float(np.dot(s.credits[chosen],fees[chosen]))
        remaining_capital=capital-credit
        selected_fee=selected_fee_capital/credit
        remaining_fee=(fee_capital-selected_fee_capital)/remaining_capital
        if draw==0:
            for i,name in enumerate(s.names):
                node_rows.append(dict(method=method,node=name,eligible_minipools_before=int(s.sizes[i]),
                    minipools_selected=int(counts[i]),fraction_removed=float(removed[i]),
                    eligible_minipools_remaining=int(s.sizes[i]-counts[i]),
                    contract_staking_minipools_remaining=int(s.full_sizes[i]-counts[i]),
                    contract_active_megapool_count=int(s.node_table.loc[name,'megapool_active_validator_count']),
                    scope='representative draw 0; not a mean over simulations'))
        rows.append(dict(method=method,draw=draw,
            **original,
            mean_fraction_removed_all_nodes_pct=100*removed.mean(),
            mean_fraction_removed_touched_nodes_pct=100*removed[touched].mean(),
            mean_fraction_removed_touched_multi_nodes_pct=100*removed[touched&multi].mean(),
            multi_nodes_losing_at_least_half=int(((2*counts>=s.sizes)&multi).sum()),
            single_pool_nodes_wiped=int((wiped&~multi).sum()),
            multi_pool_nodes_wiped=int((wiped&multi).sum()),
            wiped_without_contract_active_megapool=int((wiped&~s.mega).sum()),
            selected_capital_weighted_commission_pct=100*selected_fee,
            remaining_eligible_capital_weighted_commission_pct=100*remaining_fee,
            validator_principal_removed_eth=32*k,
            operator_bond_returned_eth=32*k-credit,
            selected_commission_weighted_capital_eth=selected_fee_capital,
            remaining_eligible_capital_eth=remaining_capital,
            remaining_eligible_user_reward_factor=1-remaining_fee))

    record('Validator index',0,s.order('Validator index'))
    for method in METHODS[:2]:
        for row in pointers.itertuples():
            record(method,int(row.draw),s.order(method,pointer=row.starting_validator_index))
    trng=np.random.default_rng(np.random.SeedSequence([seed,1]))
    brng=np.random.default_rng(np.random.SeedSequence([seed,2]))
    for draw in range(meta['draws']):
        record('Random ties',draw,s.order('Random ties',random=trng.random(len(s.df))))
        record('Random baseline',draw,s.order('Random baseline',random=brng.random(len(s.df))))
    details=pd.DataFrame(rows)
    assert len(details)==len(saved)
    details.to_csv(ROOT/'post_details_draws.csv',index=False)
    pd.DataFrame(node_rows).to_csv(ROOT/'node_fraction_removed.csv',index=False)
    summaries=[]
    for method,group in details.groupby('method',sort=False):
        for metric in group.columns.drop(['method','draw']):
            v=group[metric]
            summaries.append(dict(method=method,metric=metric,draws=len(v),mean=v.mean(),p05=v.quantile(.05),p95=v.quantile(.95)))
    pd.DataFrame(summaries).to_csv(ROOT/'post_details_summary.csv',index=False)
    # This retained-RPL/commission weighting makes no assumption of forced sales.
    dash=json.loads((ROOT/'sources/rocketdash_crosscheck.json').read_text())
    from decimal import Decimal
    supply=Decimal(dash['data']['rethSupplyWei'])/WEI
    tvl=supply*Decimal(s.rate)/WEI
    book=dict(seed=seed,demand_reth=50000,strict_cap=True,replayed_saved_draws=len(details),
              clustering_source='clustering_original.json; original seed 20261005, not later seed 20261006',
              eligible_capital_eth=capital,eligible_capital_weighted_commission_pct=100*fee_capital/capital,
              fraction_denominator='eligible minipools per node; unweighted averages over node addresses; touched-only and all-node scopes kept separate',
              full_node_limit='No beacon join for megapools; contract active count is a proxy and may include queued/exiting validators',
              yield_model='Equal gross reward rate per funded ETH and static contract commission; retained user reward factor = 1 - capital-weighted commission; no measured realised APR',
              gross_apr_example=0.03,
              near_snapshot_reth_supply=str(supply),near_snapshot_reth_backing_eth=str(tvl),
              supply_source_block=dash['data']['sourceTokensSyncBlock'],
              hypothetical_50000_reth_redemption_supply_fraction_pct=float(Decimal(50000)/supply*100),
              hypothetical_backing_after_50000_reth_redemption_eth=str(tvl-Decimal(50000)*Decimal(s.rate)/WEI),
              alternatives='Only all-random baseline and randomized ties already modeled; no node-balanced or round-robin algorithm tested')
    (ROOT/'post_details.json').write_text(json.dumps(book,indent=2)+'\n')
    print(pd.DataFrame(summaries).pivot(index='method',columns='metric',values='mean')[[
        'mean_fraction_removed_touched_nodes_pct','mean_fraction_removed_touched_multi_nodes_pct',
        'single_pool_nodes_wiped','multi_pool_nodes_wiped','multi_nodes_losing_at_least_half',
        'wiped_without_contract_active_megapool','remaining_eligible_capital_weighted_commission_pct']].to_string())


if __name__=='__main__':
    main()
