"""Compare saved strict-cap exit metrics across the three request sizes."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
STYLES=[('Soonest sweep','#145b78','o'),('Latest sweep','#cf9740','s'),
        ('Random ties','#418f80','^'),('Validator index','#8b5c9a','D')]


def main():
    meta=json.loads((ROOT/'results/results.json').read_text())
    seed=meta['seeds'][0]
    summary=pd.read_csv(ROOT/'results/summary.csv')
    demands=[10000,50000,200000]
    metrics=['nodes_wiped','top10_node_share_pct']
    selected=summary[(summary.seed==seed)&(summary.overshoot_rule=='strict_cap')&
                     summary.demand_reth.isin(demands)&summary.metric.isin(metrics)].copy()
    assert len(selected)==30
    assert not selected.duplicated(['method','metric','demand_reth']).any()
    selected.to_csv(ROOT/'results/exit_concentration_by_size.csv',index=False)

    def rows(method,metric):
        return selected[(selected.method==method)&(selected.metric==metric)].set_index('demand_reth').loc[demands]

    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    fig,axes=plt.subplots(1,2,figsize=(13,5.5),layout='constrained')
    fig.set_layout_engine('constrained',rect=(0,.09,1,.91))
    positions=np.arange(3,dtype=float)
    handles=[]
    for ax,metric,label in zip(axes,metrics,
            ['Eligible minipool books wiped','Top-10 node share (%)']):
        baseline=rows('Random baseline',metric)
        ax.fill_between(positions,baseline.p05.to_numpy(),baseline.p95.to_numpy(),color='#cbd4df',alpha=.6,zorder=1)
        base,=ax.plot(positions,baseline['mean'].to_numpy(),color='#677788',marker='X',linestyle='--',
                     linewidth=2,markersize=7,label='Random baseline',zorder=4)
        for offset,(method,color,marker) in zip([-.12,-.04,.04,.12],STYLES):
            r=rows(method,metric)
            y=r['mean'].to_numpy()
            # Quantiles need not enclose the mean; draw absolute endpoints.
            ax.vlines(positions+offset,r.p05.to_numpy(),r.p95.to_numpy(),color=color,linewidth=1.2,alpha=.8,zorder=2)
            ax.scatter(positions+offset,r.p05.to_numpy(),marker='_',color=color,s=35,zorder=2)
            ax.scatter(positions+offset,r.p95.to_numpy(),marker='_',color=color,s=35,zorder=2)
            line,=ax.plot(positions+offset,y,color=color,marker=marker,markersize=7,linewidth=1.7,
                          label=method,zorder=3)
            if metric==metrics[0]:
                handles.append(line)
        if metric==metrics[0]:
            handles.append(base)
            for x,y in zip(positions,baseline['mean']):
                if x==0:
                    continue  # The 10k mean sits too close to the x-axis label.
                ax.annotate(f'{y:,.1f}',(x,y),xytext=(0,-18),textcoords='offset points',
                            ha='center',fontsize=9,color='#526271')
        ax.set(xticks=positions,xticklabels=['10k','50k','200k'],xlabel='Net shortfall (rETH)',
               ylabel=label,xlim=(-.3,2.3))
        ax.grid(axis='y',alpha=.2)
    axes[0].set_ylim(0,1300)
    axes[1].set_ylim(0,90)
    axes[1].yaxis.set_major_formatter(PercentFormatter(100,decimals=0))

    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,0),ncol=5,frameon=False,fontsize=10)
    for suffix in ['png','pdf','svg']:
        fig.savefig(ROOT/f'figures/exit_concentration_by_size.{suffix}',dpi=220)
    plt.close(fig)
    print(selected[selected.metric=='top10_node_share_pct'].pivot(index='method',columns='demand_reth',values='mean').to_string())


if __name__=='__main__':
    main()
