"""Offline RPIP-71 minipool ordering comparison; run: python simulate.py.

Exact integer commissions and wei caps; a priority prefix never skips a row.
Independent RNG streams make draw orders paired across demand/overshoot tests.
"""
import argparse
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
WEI = 10**18
METHODS = ['Soonest sweep', 'Latest sweep', 'Random ties', 'Validator index', 'Random baseline']
KEYS = ['validators_selected', 'nodes_touched', 'nodes_wiped', 'exits_on_wiped_nodes_pct',
        'top10_node_share_pct', 'rpl_on_wiped_nodes', 'conservative_full_nodes_wiped',
        'wiped_nodes_with_megapool', 'legacy_rpl_on_wiped_nodes', 'credited_eth', 'cap_gap_eth']


def prefix_length(cumulative_eth, cap_wei, rule):
    """Largest prefix <= cap; sensitivity includes the first cap-crossing row."""
    if cap_wei <= 0:
        return 0
    k = int(np.searchsorted(cumulative_eth, cap_wei // WEI, side='right'))
    if rule == 'include_crossing' and k < len(cumulative_eth):
        if k == 0 or int(cumulative_eth[k-1])*WEI < cap_wei:
            k += 1
    return k


class Simulation:
    def __init__(self):
        self.meta = json.loads((ROOT / 'snapshot.json').read_text())
        raw = pd.read_csv(ROOT / 'minipools.csv', dtype=str, keep_default_na=False)
        self.node_table = pd.read_csv(ROOT / 'nodes.csv', dtype=str, keep_default_na=False).set_index('node')
        assert len(raw) == self.meta['staking_count']
        assert raw.snapshot_block.eq(str(self.meta['block'])).all()
        for key in ['minipool', 'pubkey', 'validator_index']:
            assert raw[key].is_unique and raw[key].ne('').all()
        eligible = (raw.beacon_status.eq('active_ongoing') & raw.exit_epoch.eq(str(2**64-1)) & raw.slashed.eq('False'))
        assert eligible.equals(raw.eligible.eq('True'))
        assert raw.bond_wei.isin([str(8*WEI), str(16*WEI)]).all()
        self.df = raw[eligible].sort_values('minipool').reset_index(drop=True)
        self.fees = self.df.commission_wei.map(int).to_numpy(dtype=np.int64)
        self.indices = self.df.validator_index.map(int).to_numpy(dtype=np.int64)
        self.credits = self.df.bond_wei.map(lambda x: 32-int(x)//WEI).to_numpy(dtype=np.int64)
        assert all(int(u) == int(c)*WEI for u, c in zip(self.df.user_deposit_wei, self.credits))
        self.nodes, self.names = pd.factorize(self.df.node, sort=True)
        self.sizes = np.bincount(self.nodes)
        self.full_sizes = raw.groupby('node').size().reindex(self.names).to_numpy()
        nt = self.node_table.reindex(self.names)
        assert nt.notna().all().all()
        for col in ['node_rpl_wei', 'node_legacy_rpl_wei', 'node_megapool_rpl_wei', 'megapool_active_validator_count']:
            assert all(self.node_table.loc[n, col] == v for n, v in zip(raw.node, raw[col]))
        self.rpl = nt.node_rpl_wei.map(lambda x: int(x)/WEI).to_numpy()
        self.legacy_rpl = nt.node_legacy_rpl_wei.map(lambda x: int(x)/WEI).to_numpy()
        self.mega = nt.megapool_active_validator_count.map(int).to_numpy() > 0
        self.rate = int(self.meta['reth_exchange_rate_wei'])

    def cap(self, demand):
        return max(0, demand*self.rate-120*WEI)

    def counts(self, selected):
        return np.bincount(self.nodes[selected], minlength=len(self.names))

    def metrics(self, selected, cap):
        counts = self.counts(selected)
        wiped = (counts == self.sizes) & (counts > 0)
        conservative = wiped & (counts == self.full_sizes) & ~self.mega
        n = len(selected)
        credit = int(self.credits[selected].sum())
        return dict(validators_selected=n, nodes_touched=int((counts>0).sum()), nodes_wiped=int(wiped.sum()),
                    exits_on_wiped_nodes_pct=float(100*counts[wiped].sum()/n) if n else 0.,
                    top10_node_share_pct=float(100*np.sort(counts)[-10:].sum()/n) if n else 0.,
                    rpl_on_wiped_nodes=float(self.rpl[wiped].sum()),
                    legacy_rpl_on_wiped_nodes=float(self.legacy_rpl[wiped].sum()),
                    conservative_full_nodes_wiped=int(conservative.sum()),
                    wiped_nodes_with_megapool=int((wiped & self.mega).sum()),
                    credited_eth=credit, cap_gap_eth=float(Decimal(cap-credit*WEI)/WEI))

    def order(self, method, pointer=None, random=None):
        if method == 'Soonest sweep':
            return np.lexsort((self.indices, self.indices < pointer, -self.fees))
        if method == 'Latest sweep':
            return np.lexsort((-self.indices, self.indices >= pointer, -self.fees))
        if method == 'Validator index':
            return np.lexsort((self.indices, -self.fees))
        if method == 'Random ties':
            return np.lexsort((random, -self.fees))
        return np.argsort(random, kind='stable')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=20261007)
    parser.add_argument('--alternate-seed', type=int, default=20261008)
    parser.add_argument('--draws', type=int, default=1000)
    parser.add_argument('--pointers', type=int, default=20)
    parser.add_argument('--demands', type=int, nargs='+', default=[50000, 10000, 200000])
    args = parser.parse_args()
    assert args.seed != args.alternate_seed and args.draws >= 1000
    s = Simulation()
    records, pointers, representatives = [], [], {}
    for seed in [args.seed, args.alternate_seed]:
        # Streams 0: pointers, 1: random ties, 2: all-random baseline. PCG64.
        prng = np.random.default_rng(np.random.SeedSequence([seed, 0]))
        sampled = prng.choice(np.sort(s.indices), size=args.pointers, replace=False)
        for draw, pointer in enumerate(sampled):
            pointers.append(dict(seed=seed, draw=draw, starting_validator_index=int(pointer)))
        orders = [('Validator index', 0, None, s.order('Validator index'))]
        orders += [(m, i, int(p), s.order(m, pointer=p)) for m in METHODS[:2] for i, p in enumerate(sampled)]
        trng = np.random.default_rng(np.random.SeedSequence([seed, 1]))
        brng = np.random.default_rng(np.random.SeedSequence([seed, 2]))

        def record(method, draw, pointer, order):
            cumulative = np.cumsum(s.credits[order])
            for demand in args.demands:
                cap = s.cap(demand)
                for rule in ['strict_cap', 'include_crossing']:
                    k = prefix_length(cumulative, cap, rule)
                    chosen = order[:k]
                    if rule == 'strict_cap':
                        assert int(s.credits[chosen].sum())*WEI <= cap
                        assert k == len(order) or int(cumulative[k])*WEI > cap
                    elif k < len(order):
                        assert int(cumulative[k-1])*WEI >= cap
                        assert k == 1 or int(cumulative[k-2])*WEI < cap
                    records.append(dict(seed=seed, demand_reth=demand, overshoot_rule=rule, method=method,
                                        draw=draw, pointer=pointer, **s.metrics(chosen, cap)))
                    if seed == args.seed and demand == 50000 and rule == 'strict_cap' and draw == 0:
                        representatives[method] = (order, k, pointer)

        for method, draw, pointer, order in orders:
            record(method, draw, pointer, order)
        for draw in range(args.draws):
            record('Random ties', draw, None, s.order('Random ties', random=trng.random(len(s.df))))
            record('Random baseline', draw, None, s.order('Random baseline', random=brng.random(len(s.df))))
        print(f'Completed seed {seed}: {len(records):,} scenario draws', flush=True)
    draws = pd.DataFrame(records)
    draws.to_csv(ROOT / 'draws.csv', index=False)
    pd.DataFrame(pointers).to_csv(ROOT / 'sweep_pointers.csv', index=False)
    summaries = []
    for (seed, demand, rule, method), group in draws.groupby(['seed', 'demand_reth', 'overshoot_rule', 'method'], sort=False):
        for key in KEYS:
            v = group[key]
            summaries.append(dict(seed=seed, demand_reth=demand, overshoot_rule=rule, method=method, metric=key,
                                  draws=len(v), mean=v.mean(), p05=v.quantile(.05), p95=v.quantile(.95), minimum=v.min(), maximum=v.max()))
    summary = pd.DataFrame(summaries)
    summary.to_csv(ROOT / 'summary.csv', index=False)
    selected_rows, node_rows = [], []
    for method, (order, k, pointer) in representatives.items():
        rows = s.df.iloc[order[:min(k+1, len(order))]].copy()
        rows.insert(0, 'method', method)
        rows['rank'] = np.arange(1, len(rows)+1)
        rows['selected'] = rows['rank'] <= k
        rows['credit_eth'] = s.credits[order[:len(rows)]]
        rows['cumulative_credit_eth'] = rows.credit_eth.cumsum()
        rows['pointer'] = pointer
        selected_rows.append(rows)
        counts = s.counts(order[:k])
        for i, name in enumerate(s.names):
            if counts[i]:
                node_rows.append(dict(method=method, node=name, exits=int(counts[i]), eligible_minipools=int(s.sizes[i]),
                                      all_staking_minipools=int(s.full_sizes[i]), wiped=bool(counts[i]==s.sizes[i]),
                                      has_megapool=bool(s.mega[i]), rpl=s.node_table.loc[name, 'node_rpl_wei']))
    pd.concat(selected_rows).to_csv(ROOT / 'representative_prefixes.csv', index=False)
    pd.DataFrame(node_rows).to_csv(ROOT / 'representative_nodes.csv', index=False)
    metadata = dict(snapshot=s.meta, seeds=[args.seed, args.alternate_seed], demands=args.demands,
                    draws=args.draws, sweep_positions=args.pointers, rng='NumPy PCG64 / SeedSequence([seed, stream])',
                    streams={'pointers':0, 'random_ties':1, 'baseline':2}, other_liquidity_eth=0,
                    demand_interpretation='rETH-sized NET shortfall, not gross queue demand; existing exits/liquidity are assumed netted out',
                    cap_wei={str(d):str(s.cap(d)) for d in args.demands}, rate_wei=str(s.rate),
                    prefix='largest strict priority prefix at/below cap; no skipping',
                    overshoot='include first crossing validator; sensitivity only, violates draft hard cap',
                    wiped_definition='all eligible minipools selected; not necessarily every validator on the node',
                    conservative_full_wipe='all contract-staking minipools selected AND zero contract active megapool count',
                    rpl_scope='total staked RPL counted once per wiped node; exposure, not loss or predicted selling',
                    sweep_sampling='20 distinct uniform eligible-validator-index starting positions; rotation sensitivity, not network cursor probabilities',
                    versions={x.__name__:x.__version__ for x in [np,pd,matplotlib]})
    (ROOT / 'results.json').write_text(json.dumps(metadata, indent=2)+'\n')
    write_table_and_chart(summary, args.seed)
    write_sanity(s, representatives, summary, args)


def write_table_and_chart(summary, seed):
    primary = summary[(summary.seed==seed)&(summary.demand_reth==50000)&(summary.overshoot_rule=='strict_cap')]
    table = ['| Commission tie-break / baseline | Nodes touched | Eligible minipool books wiped | Exits on wiped nodes | Top-10 node share | RPL on wiped nodes |',
             '|---|---:|---:|---:|---:|---:|']
    for method in METHODS:
        cells = []
        for metric in KEYS[1:6]:
            r = primary[(primary.method==method)&(primary.metric==metric)].iloc[0]
            places = 1 if metric != 'rpl_on_wiped_nodes' else 0
            cell = f'{r["mean"]:,.{places}f}'
            if r.draws>1:
                cell += f' [{r.p05:,.{places}f}–{r.p95:,.{places}f}]'
            if metric.endswith('_pct'):
                cell += '%'
            cells.append(cell)
        table.append('| '+method+' | '+' | '.join(cells)+' |')
    (ROOT / 'table.md').write_text('\n'.join(table)+'\n')
    plot = primary[primary.metric=='nodes_wiped'].set_index('method')
    plt.rcParams.update({'font.size':11, 'axes.spines.top':False, 'axes.spines.right':False})
    fig, ax = plt.subplots(figsize=(10.5,5.6), layout='constrained')
    baseline = plot.loc['Random baseline']
    ax.axhspan(baseline.p05, baseline.p95, color='#91a8bf', alpha=.25, label='Random 5th–95th percentile')
    ax.axhline(baseline['mean'], color='#62798c', linestyle='--', label=f'Random mean: {baseline["mean"]:.1f}')
    labels = ['Soonest sweep', 'Latest sweep', 'Random ties', 'Validator index']
    for x, method in enumerate(METHODS[:4]):
        r = plot.loc[method]
        # Quantiles may lie on one side of mean; draw interval independently.
        ax.vlines(x, r.p05, r.p95, colors='#145b78', linewidth=2.5)
        ax.plot(x, r['mean'], 'o', color='#145b78', markersize=8)
        ax.annotate(f'{r["mean"]:.1f}', (x, r['mean']), xytext=(10,7), textcoords='offset points')
    ax.set(xticks=range(4), xticklabels=labels, ylabel='Eligible minipool books wiped')
    ax.set_xlim(-.5,3.7)
    ax.set_ylim(0, max(plot.p95)*1.16)
    ax.grid(axis='y',alpha=.2)
    ax.legend(loc='lower left', fontsize=9)
    for suffix in ['png','pdf','svg']:
        fig.savefig(ROOT / f'nodes_wiped.{suffix}', dpi=200)
    plt.close(fig)


def write_sanity(s, reps, summary, args):
    # Independent Python/Decimal/Counter reconciliation; no vectorized metric code.
    order, k, _ = reps['Validator index']
    ordered = s.df.iloc[order].to_dict('records')
    cap = Decimal(s.cap(50000))/WEI
    total = Decimal(0)
    chosen = []
    for row in ordered:
        credit = Decimal(32)-Decimal(row['bond_wei'])/WEI
        if total+credit > cap:
            next_credit = credit
            break
        total += credit
        chosen.append(row)
    counts = Counter(row['node'] for row in chosen)
    sizes = Counter(s.df.node)
    wiped = {node for node, count in counts.items() if count==sizes[node]}
    exact_rpl = sum(int(s.node_table.loc[node,'node_rpl_wei']) for node in wiped)
    manual = dict(validators_selected=len(chosen), credited_eth=int(total), nodes_touched=len(counts), nodes_wiped=len(wiped),
                  exits_on_wiped_nodes_pct=100*sum(counts[n] for n in wiped)/len(chosen),
                  top10_node_share_pct=100*sum(sorted(counts.values(),reverse=True)[:10])/len(chosen),
                  rpl_on_wiped_nodes=float(Decimal(exact_rpl)/WEI))
    expected = s.metrics(order[:k], s.cap(50000))
    for key, value in manual.items():
        assert np.isclose(value, expected[key], rtol=1e-12, atol=1e-9), (key,value,expected[key])
    assert len(chosen)==k
    # Audit signs per seed/rule/demand against the mean baseline; no assumed outcome.
    comparisons = []
    for seed in [args.seed,args.alternate_seed]:
        for demand in args.demands:
            for rule in ['strict_cap','include_crossing']:
                part = summary[(summary.seed==seed)&(summary.demand_reth==demand)&(summary.overshoot_rule==rule)]
                for method in METHODS[:4]:
                    for key in KEYS[:9]:
                        r = part[(part.method==method)&(part.metric==key)].iloc[0]
                        b = part[(part.method=='Random baseline')&(part.metric==key)].iloc[0]
                        comparisons.append(dict(seed=seed,demand_reth=demand,overshoot_rule=rule,method=method,metric=key,
                                                method_mean=r['mean'],baseline_mean=b['mean'],difference=r['mean']-b['mean'],
                                                above_baseline_p95=bool(r['mean']>b.p95)))
    comparison = pd.DataFrame(comparisons)
    comparison.to_csv(ROOT / 'robustness.csv',index=False)
    signs = comparison.assign(sign=np.sign(comparison.difference)).groupby(['demand_reth','method','metric']).sign.nunique()
    flips = [dict(demand_reth=int(d),method=m,metric=k) for (d,m,k),v in signs.items() if v>1]
    # Paired overshoot delta for every draw.
    differences = []
    for key, group in pd.read_csv(ROOT/'draws.csv').groupby(['seed','demand_reth','method'],sort=False):
        strict = group[group.overshoot_rule=='strict_cap'].set_index('draw')
        crossing = group[group.overshoot_rule=='include_crossing'].set_index('draw')
        for metric in KEYS[:9]:
            delta = crossing[metric]-strict[metric]
            differences.append(dict(seed=key[0],demand_reth=key[1],method=key[2],metric=metric,
                                    mean_delta=delta.mean(),max_absolute_delta=delta.abs().max()))
    pd.DataFrame(differences).to_csv(ROOT/'overshoot_deltas.csv',index=False)
    sanity = dict(independent_reconciliation=manual,request_cap_eth=str(cap),next_credit_eth=str(next_credit),
                  prefix_gap_eth=str(cap-total),including_next_exceeds_cap_eth=str(total+next_credit-cap),
                  sign_flips_across_seeds_and_overshoot=flips,
                  spreadsheet_status='Formula workbook with independently computed cached values; recalculate in a spreadsheet application for application-level verification')
    (ROOT/'sanity.json').write_text(json.dumps(sanity,indent=2)+'\n')
    make_spreadsheet(s,ordered,chosen,manual,cap,next_credit)
    print(json.dumps(sanity,indent=2),flush=True)


def make_spreadsheet(s, ordered, chosen, manual, cap, next_credit):
    import xlsxwriter
    wb = xlsxwriter.Workbook(ROOT/'hand_check.xlsx')
    header = wb.add_format({'bold':True,'bg_color':'#dceaf1'})
    integer = wb.add_format({'num_format':'#,##0'})
    decimal = wb.add_format({'num_format':'#,##0.000000'})
    control = wb.add_worksheet('Control')
    inputs = [('Block',s.meta['block']),('ETH/rETH',float(Decimal(s.rate)/WEI)),('Net shortfall rETH',50000),('Hysteresis ETH',120)]
    for r,(label,value) in enumerate(inputs):
        control.write(r,0,label); control.write_number(r,1,value)
    control.write(4,0,'Request cap ETH'); control.write_formula(4,1,'=B2*B3-B4',decimal,float(cap))
    control.write(6,0,'Scenario'); control.write(6,1,'Commission descending, validator index ascending, strict cap')
    control.write(7,0,'Precision'); control.write(7,1,'CSV/script use exact wei; Excel floating precision cannot reproduce wei. Boundary margin exceeds 8 ETH.')
    control.write(8,0,'Wiped'); control.write(8,1,'All eligible minipools selected; nodes may retain other validators.')
    control.set_column(0,0,30); control.set_column(1,1,115)
    prefix = wb.add_worksheet('Prefix')
    prefix.write_row(0,0,['Rank','Minipool','Node','Exact fee wei (text)','Validator index','Bond ETH','Credit ETH','Cumulative ETH','Selected'],header)
    cumulative = 0
    for i,row in enumerate(ordered[:len(chosen)+1],start=1):
        bond = int(row['bond_wei'])//WEI; cumulative += 32-bond
        prefix.write_row(i,0,[i,row['minipool'],row['node'],row['commission_wei'],int(row['validator_index']),bond])
        prefix.write_formula(i,6,f'=32-F{i+1}',integer,32-bond)
        prefix.write_formula(i,7,f'=G{i+1}'+(f'+H{i}' if i>1 else ''),integer,cumulative)
        prefix.write_formula(i,8,f'=IF(H{i+1}<=Control!$B$5,1,0)',integer,int(i<=len(chosen)))
    prefix.freeze_panes(1,0); prefix.autofilter(0,0,len(chosen)+1,8)
    prefix.set_column(0,0,9); prefix.set_column(1,2,45); prefix.set_column(3,3,22); prefix.set_column(4,8,18)
    last = len(chosen)+2
    node_sheet = wb.add_worksheet('Nodes')
    node_sheet.write_row(0,0,['Node','Eligible minipools','Selected','Wiped','Exits on wiped','Total RPL','RPL on wiped'],header)
    counts = Counter(row['node'] for row in chosen)
    for i,name in enumerate(s.names,start=1):
        exits = counts.get(name,0); wiped=int(exits==s.sizes[i-1] and exits>0); rpl=float(s.rpl[i-1])
        node_sheet.write_row(i,0,[name,int(s.sizes[i-1])])
        node_sheet.write_formula(i,2,f'=SUMIF(Prefix!$C$2:$C${last},A{i+1},Prefix!$I$2:$I${last})',integer,exits)
        node_sheet.write_formula(i,3,f'=IF(AND(C{i+1}=B{i+1},C{i+1}>0),1,0)',integer,wiped)
        node_sheet.write_formula(i,4,f'=C{i+1}*D{i+1}',integer,exits*wiped)
        node_sheet.write_number(i,5,rpl,decimal)
        node_sheet.write_formula(i,6,f'=F{i+1}*D{i+1}',decimal,rpl*wiped)
    nlast = len(s.names)+1
    node_sheet.set_column(0,0,45); node_sheet.set_column(1,7,19); node_sheet.freeze_panes(1,0)
    check = wb.add_worksheet('Check')
    check.write_row(0,0,['Metric','Spreadsheet formula','Independent Python value','Difference'],header)
    equations = [
        ('validators_selected',f'=SUM(Prefix!I2:I{last})'),
        ('credited_eth',f'=SUMPRODUCT(Prefix!G2:G{last},Prefix!I2:I{last})'),
        ('nodes_touched',f'=COUNTIF(Nodes!C2:C{nlast},">0")'),
        ('nodes_wiped',f'=SUM(Nodes!D2:D{nlast})'),
        ('exits_on_wiped_nodes_pct',f'=100*SUM(Nodes!E2:E{nlast})/B2'),
        ('top10_node_share_pct','=100*('+ '+'.join(f'LARGE(Nodes!C2:C{nlast},{i})' for i in range(1,11))+')/B2'),
        ('rpl_on_wiped_nodes',f'=SUM(Nodes!G2:G{nlast})')]
    for i,(key,formula) in enumerate(equations,start=1):
        value=manual[key]; check.write(i,0,key)
        check.write_formula(i,1,formula,decimal,value); check.write_number(i,2,value,decimal)
        check.write_formula(i,3,f'=B{i+1}-C{i+1}',decimal,0)
    check.write(10,0,'Next validator credit'); check.write_number(10,1,float(next_credit))
    check.write(11,0,'Unused strict cap'); check.write_formula(11,1,'=Control!B5-B3',decimal,float(cap-manual['credited_eth']))
    check.write(12,0,'Crossing overshoot'); check.write_formula(12,1,'=B3+B11-Control!B5',decimal,float(Decimal(manual['credited_eth'])+next_credit-cap))
    check.set_column(0,0,32); check.set_column(1,3,24)
    wb.close()


if __name__=='__main__':
    main()
