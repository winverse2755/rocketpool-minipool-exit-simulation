"""Publication PNGs from existing clustering and simulation summaries."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
TEAL='#145b78'
GRAY='#879cae'
GOLD='#cf9740'


def main():
    plt.rcParams.update({'font.size':11,'axes.spines.top':False,'axes.spines.right':False})
    c=json.loads((ROOT/'clustering_original.json').read_text())['clustering']
    keys=['homogeneous_nodes_pct','homogeneous_multi_nodes_pct','same_commission_within_node_pairs_pct']
    labels=['Homogeneous nodes\nAll (1,323)','Homogeneous nodes\nMulti-minipool (873)','Same-commission pairs']
    observed=[c[k]['observed'] for k in keys]
    random=[c[k]['random']['mean'] for k in keys]
    fig,ax=plt.subplots(figsize=(11.5,5.8),layout='constrained')
    positions=np.arange(3)
    bars=ax.bar(positions-.18,observed,width=.36,color=TEAL,label='Observed',zorder=3)
    null=ax.bar(positions+.18,random,width=.36,color=GRAY,label='Randomized mean',zorder=3)
    for group in [bars,null]:
        ax.bar_label(group,labels=[f'{b.get_height():.2f}%' for b in group],padding=5,fontsize=12)
    ax.set(xticks=positions,xticklabels=labels,ylabel='Share (%)',ylim=(0,100))
    ax.yaxis.set_major_formatter(PercentFormatter(100,decimals=0))
    ax.grid(axis='y',alpha=.2,zorder=0)
    ax.legend(loc='upper center',ncol=2,frameon=False,fontsize=10)
    fig.savefig(ROOT/'commission_clustering.png',dpi=200)
    plt.close(fig)

    metrics=pd.read_csv(ROOT/'post_details_summary.csv')
    def mean(method,key):
        return float(metrics[(metrics.method==method)&(metrics.metric==key)].iloc[0]['mean'])
    methods=['Soonest sweep','Random baseline']
    names=['Commission +\nsoonest sweep','Random\nbaseline']
    fees=[mean(m,'remaining_eligible_capital_weighted_commission_pct') for m in methods]
    user=[mean(m,'credited_eth')/1000 for m in methods]
    bonds=[mean(m,'operator_bond_returned_eth')/1000 for m in methods]
    fig,axes=plt.subplots(1,2,figsize=(11.5,5.5),layout='constrained')
    bars=axes[0].bar([0,1],fees,color=[TEAL,GRAY],width=.55,zorder=3)
    axes[0].bar_label(bars,labels=[f'{v:.2f}%' for v in fees],padding=6,fontsize=13)
    axes[0].set(xticks=[0,1],xticklabels=names,ylim=(0,14),ylabel='Remaining capital-weighted commission (%)')
    axes[0].yaxis.set_major_formatter(PercentFormatter(100,decimals=0))
    first=axes[1].bar([0,1],user,color=TEAL,width=.55,label='rETH-funded principal',zorder=3)
    second=axes[1].bar([0,1],bonds,bottom=user,color=GOLD,width=.55,label='Operator bond returned',zorder=3)
    for i in range(2):
        axes[1].text(i,user[i]/2,f'{user[i]:.1f}k',ha='center',va='center',color='white',fontsize=13)
        axes[1].text(i,user[i]+bonds[i]/2,f'{bonds[i]:.1f}k',ha='center',va='center',fontsize=13)
        axes[1].text(i,user[i]+bonds[i]+2,f'{user[i]+bonds[i]:.1f}k ETH',ha='center',fontsize=12)
    axes[1].set(xticks=[0,1],xticklabels=names,ylim=(0,120),ylabel='Validator principal removed (k ETH)')
    axes[1].legend(loc='upper right',fontsize=9,frameon=False)
    for ax in axes:
        ax.grid(axis='y',alpha=.2,zorder=0)
    fig.savefig(ROOT/'reth_efficiency.png',dpi=200)
    plt.close(fig)
    print('Created commission_clustering.png and reth_efficiency.png')


if __name__=='__main__':
    main()
