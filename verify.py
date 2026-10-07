"""Verify prefix boundaries, audit CSV, paired draws, and spreadsheet values."""
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

from simulate import ROOT, WEI, prefix_length


def main():
    # Prefix cannot skip a large row to admit a later small row. Exact-wei caps
    # on both sides of equality catch off-by-one and rounding errors.
    cumulative = np.array([24,48,64])
    cases = [(0,0,0),(23*WEI,0,1),(24*WEI,1,1),
             (24*WEI+1,1,2),(48*WEI-1,1,2),(48*WEI,2,2),
             (64*WEI,3,3),(100*WEI,3,3)]
    for cap, strict, crossing in cases:
        assert prefix_length(cumulative,cap,'strict_cap')==strict
        assert prefix_length(cumulative,cap,'include_crossing')==crossing
    audit=pd.read_csv(ROOT/'representative_prefixes.csv',dtype=str)
    node_info=pd.read_csv(ROOT/'nodes.csv',dtype=str).set_index('node')
    raw=pd.read_csv(ROOT/'minipools.csv',dtype=str)
    sizes=Counter(raw[raw.eligible.eq('True')].node)
    result={}
    meta=json.loads((ROOT/'results.json').read_text())
    for method, group in audit.groupby('method'):
        fees=group.commission_wei.map(int).tolist()
        if method!='Random baseline':
            assert all(a>=b for a,b in zip(fees,fees[1:]))
        if method=='Validator index':
            keys=list(zip([-v for v in fees],group.validator_index.map(int)))
            assert keys==sorted(keys)
        if method in ['Soonest sweep','Latest sweep']:
            p=int(group.pointer.iloc[0]); indices=group.validator_index.map(int).tolist()
            ties=[(int(v<p),v) if method=='Soonest sweep' else (int(v>=p),-v) for v in indices]
            keys=[(-f,*t) for f,t in zip(fees,ties)]
            assert keys==sorted(keys)
        total=0; counts=Counter()
        cap=int(meta['cap_wei']['50000'])
        for row in group.to_dict('records'):
            credit=32-int(row['bond_wei'])//WEI
            total+=credit
            assert total==int(row['cumulative_credit_eth'])
            assert (row['selected']=='True')==(total*WEI<=cap)
            if row['selected']=='True':
                counts[row['node']]+=1
        wiped=[n for n,c in counts.items() if c==sizes[n]]
        rpl=sum(int(node_info.loc[n,'node_rpl_wei']) for n in wiped)
        result[method]=dict(exits=sum(counts.values()),nodes=len(counts),wiped=len(wiped),rpl=str(Decimal(rpl)/WEI))
    draws=pd.read_csv(ROOT/'draws.csv')
    assert not draws.duplicated(['seed','demand_reth','overshoot_rule','method','draw']).any()
    for key, group in draws.groupby(['seed','demand_reth','overshoot_rule','method']):
        expected=meta['draws'] if key[3] in ['Random ties','Random baseline'] else (meta['sweep_positions'] if 'sweep' in key[3] else 1)
        assert len(group)==expected
    keys=['seed','demand_reth','method','draw']
    strict=draws[draws.overshoot_rule=='strict_cap'].set_index(keys)
    crossing=draws[draws.overshoot_rule=='include_crossing'].set_index(keys)
    delta=crossing.validators_selected-strict.validators_selected
    assert delta.isin([0,1]).all()
    assert (strict.cap_gap_eth>=0).all()
    assert (crossing.cap_gap_eth<=0).all()
    assert (crossing.cap_gap_eth > -24).all()
    workbook=ROOT/'hand_check_recalculated.xlsx'
    if workbook.exists():
        wb=openpyxl.load_workbook(workbook,data_only=True)
        candidates=[sheet for sheet in wb if sheet['A1'].value=='Metric']
        assert len(candidates)==1, wb.sheetnames
        sheet=candidates[0]
        spreadsheet={}
        current_expected=json.loads((ROOT/'sanity.json').read_text())['independent_reconciliation']
        for row in range(2,9):
            metric, calculated, expected, delta=[sheet.cell(row,col).value for col in range(1,5)]
            assert isinstance(calculated,(float,int)), (metric,calculated)
            assert np.isclose(calculated,expected,rtol=1e-12,atol=1e-8), (metric,calculated,expected)
            assert np.isclose(calculated,current_expected[metric],rtol=1e-12,atol=1e-8), (metric,'stale spreadsheet')
            spreadsheet[metric]={'calculated':calculated,'expected':expected,'difference':delta}
        result['spreadsheet']=spreadsheet
        sanity=json.loads((ROOT/'sanity.json').read_text())
        sanity['spreadsheet_status']='PASS: opened and recalculated in Apple Numbers, exported to XLSX; seven metric formulas agree with independent reconciliation'
        (ROOT/'sanity.json').write_text(json.dumps(sanity,indent=2)+'\n')
    else:
        result['spreadsheet']='Numbers recalculated workbook absent; cached workbook alone is not proof of spreadsheet evaluation'
    (ROOT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
