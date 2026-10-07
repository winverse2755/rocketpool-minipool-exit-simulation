"""Compare saved strict-cap exit metrics across the three request sizes."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
STYLES=[('Soonest sweep','#145b78','o'),('Latest sweep','#cf9740','s'),
        ('Random ties','#418f80','^'),('Validator index','#8b5c9a','D')]


def main():
    meta=json.loads((ROOT/'results.json').read_text())
    seed=meta['seeds'][0]
    summary=pd.read_csv(ROOT/'summary.csv')
    demands=[10000,50000,200000]
    metrics=['nodes_wiped','top10_node_share_pct']
    selected=summary[(summary.seed==seed)&(summary.overshoot_rule=='strict_cap')&
                     summary.demand_reth.isin(demands)&summary.metric.isin(metrics)].copy()
    assert len(selected)==30
    assert not selected.duplicated(['method','metric','demand_reth']).any()
    selected.to_csv(ROOT/'exit_concentration_by_size.csv',index=False)

    def rows(method,metric):
        return selected[(selected.method==method)&(selected.metric==metric)].set_index('demand_reth').loc[demands]

    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(13,7),layout='constrained')
    fig.set_layout_engine('constrained',rect=(0,.17,1,.69))
    positions=np.arange(3,dtype=float)
    handles=[]
    for ax,metric,title,label in zip(axes,metrics,
            ['Eligible minipool books wiped','Top-10 share of selected validator exits'],
            ['Nodes losing all eligible minipools','Share of exits on the ten most-hit node addresses']):
        baseline=rows('Random baseline',metric)
        ax.fill_between(positions,baseline.p05.to_numpy(),baseline.p95.to_numpy(),color='#cbd4df',alpha=.6,zorder=1)
        base,=ax.plot(positions,baseline['mean'].to_numpy(),color='#677788',marker='X',linestyle='--',
                     linewidth=2,markersize=7,label='All-random baseline',zorder=4)
        for offset,(method,color,marker) in zip([-.12,-.04,.04,.12],STYLES):
            r=rows(method,metric)
            y=r['mean'].to_numpy()
            # Quantiles need not enclose the mean; draw absolute endpoints.
            ax.vlines(positions+offset,r.p05.to_numpy(),r.p95.to_numpy(),color=color,linewidth=1.2,alpha=.8,zorder=2)
            ax.scatter(positions+offset,r.p05.to_numpy(),marker='_',color=color,s=35,zorder=2)
            ax.scatter(positions+offset,r.p95.to_numpy(),marker='_',color=color,s=35,zorder=2)
            line,=ax.plot(positions+offset,y,color=color,marker=marker,markersize=7,linewidth=1.7,
                          label='Commission + '+method.lower(),zorder=3)
            if metric==metrics[0]:
                handles.append(line)
        if metric==metrics[0]:
            handles.append(base)
            for x,y in zip(positions,baseline['mean']):
                if x==0:
                    continue  # The 10k mean sits too close to the x-axis label.
                ax.annotate(f'{y:,.1f}',(x,y),xytext=(0,-18),textcoords='offset points',
                            ha='center',fontsize=9,color='#526271')
        ax.set(xticks=positions,xticklabels=['10k','50k','200k'],xlabel='Net shortfall (rETH; three discrete scenarios)',
               ylabel=label,title=title,xlim=(-.3,2.3))
        ax.grid(axis='y',alpha=.2)
    axes[0].set_ylim(0,1300)
    axes[1].set_ylim(0,90)
    axes[1].yaxis.set_major_formatter(PercentFormatter(100,decimals=0))

    # A zoom makes the 200k ordering crossover visible on a 0–90% main axis.
    zoom=axes[1].inset_axes([.56,.53,.40,.35])
    zoom.set_facecolor('#f8f9fb')
    zoom.set_title('200k detail',fontsize=10,pad=4)
    for x,(method,color,marker) in enumerate(STYLES+[('Random baseline','#677788','X')]):
        r=rows(method,metrics[1]).loc[200000]
        zoom.vlines(x,r.p05,r.p95,color=color,linewidth=1)
        zoom.plot(x,r['mean'],marker=marker,color=color,markersize=5)
        zoom.annotate(f'{r["mean"]:.2f}',(x,r['mean']),xytext=(0,7),textcoords='offset points',
                      ha='center',fontsize=7,color=color)
    zoom.set(xticks=range(5),xticklabels=['Soon','Late','Ties','Index','Rand'],ylim=(20.5,24.8),xlim=(-.5,4.5))
    zoom.yaxis.set_major_formatter(PercentFormatter(100,decimals=0))
    zoom.tick_params(labelsize=7)
    zoom.grid(axis='y',alpha=.15)

    fig.suptitle('Rocket Pool exit concentration across request sizes',fontsize=19,y=.99)
    fig.text(.5,.925,'More wiped minipool books at all three sizes; top-10 share converges at 200k',
             ha='center',fontsize=11)
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.105),ncol=3,frameon=False,fontsize=10)
    fig.text(.012,.075,'Means and 5th–95th percentile ranges: random rules 1,000 draws; sweep rules 20 rotations; validator index fixed.',fontsize=9)
    fig.text(.012,.046,'Gray band: all-random 5th–95th percentiles. Sweep ranges show rotation sensitivity, not withdrawal timing. Lines connect only the three modeled cases.',fontsize=9)
    fig.text(.012,.017,f'Block {meta["snapshot"]["block"]:,} · seed {seed} · strict cap · wiped means all eligible minipools; nodes may retain other validators.',fontsize=9)
    for suffix in ['png','pdf','svg']:
        fig.savefig(ROOT/f'exit_concentration_by_size.{suffix}',dpi=220)
    plt.close(fig)
    print(selected[selected.metric=='top10_node_share_pct'].pivot(index='method',columns='demand_reth',values='mean').to_string())


if __name__=='__main__':
    main()
