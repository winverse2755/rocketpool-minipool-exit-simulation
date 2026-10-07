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
    labels=['Homogeneous commission\nAll 1,323 nodes','Homogeneous commission\n873 multi-minipool nodes','Same-commission pairs\nAll within-node pairs']
    observed=[c[k]['observed'] for k in keys]
    random=[c[k]['random']['mean'] for k in keys]
    fig,ax=plt.subplots(figsize=(11.5,5.8),layout='constrained')
    fig.set_layout_engine('constrained',rect=(0,.09,1,.83))
    positions=np.arange(3)
    bars=ax.bar(positions-.18,observed,width=.36,color=TEAL,label='Observed snapshot',zorder=3)
    null=ax.bar(positions+.18,random,width=.36,color=GRAY,label='Randomized mean · 1,000 commission shuffles',zorder=3)
    for group in [bars,null]:
        ax.bar_label(group,labels=[f'{b.get_height():.2f}%' for b in group],padding=5,fontsize=12)
    ax.set(xticks=positions,xticklabels=labels,ylabel='Share (%)',ylim=(0,100))
    ax.yaxis.set_major_formatter(PercentFormatter(100,decimals=0))
    ax.grid(axis='y',alpha=.2,zorder=0)
    ax.legend(loc='upper center',ncol=2,frameon=False,fontsize=10)
    fig.suptitle('Commission is clustered within nodes',fontsize=18,y=.99)
    fig.text(.5,.925,'Shuffling preserves each node’s pool count and the global exact commission distribution',ha='center',fontsize=11)
    fig.text(.015,.027,'Block 26,127,238 · seed 20261005 · 450 single-minipool nodes are homogeneous in both observed and shuffled data',fontsize=9)
    fig.savefig(ROOT/'commission_clustering.png',dpi=200)
    plt.close(fig)

    metrics=pd.read_csv(ROOT/'post_details_summary.csv')
    def mean(method,key):
        return float(metrics[(metrics.method==method)&(metrics.metric==key)].iloc[0]['mean'])
    methods=['Soonest sweep','Random baseline']
    names=['Commission +\nsoonest sweep','All-random\nbaseline']
    fees=[mean(m,'remaining_eligible_capital_weighted_commission_pct') for m in methods]
    user=[mean(m,'credited_eth')/1000 for m in methods]
    bonds=[mean(m,'operator_bond_returned_eth')/1000 for m in methods]
    fig,axes=plt.subplots(1,2,figsize=(11.5,5.9),layout='constrained')
    fig.set_layout_engine('constrained',rect=(0,.13,1,.72))
    bars=axes[0].bar([0,1],fees,color=[TEAL,GRAY],width=.55,zorder=3)
    axes[0].bar_label(bars,labels=[f'{v:.2f}%' for v in fees],padding=6,fontsize=13)
    axes[0].set(xticks=[0,1],xticklabels=names,ylim=(0,14),ylabel='Remaining capital-weighted commission (%)',
                title='Lower fee burden on the remaining eligible minipool book',)
    axes[0].title.set_fontsize(11)
    axes[0].yaxis.set_major_formatter(PercentFormatter(100,decimals=0))
    first=axes[1].bar([0,1],user,color=TEAL,width=.55,label='rETH-funded principal',zorder=3)
    second=axes[1].bar([0,1],bonds,bottom=user,color=GOLD,width=.55,label='Operator bond returned',zorder=3)
    for i in range(2):
        axes[1].text(i,user[i]/2,f'{user[i]:.1f}k',ha='center',va='center',color='white',fontsize=13)
        axes[1].text(i,user[i]+bonds[i]/2,f'{bonds[i]:.1f}k',ha='center',va='center',fontsize=13)
        axes[1].text(i,user[i]+bonds[i]+2,f'{user[i]+bonds[i]:.1f}k ETH',ha='center',fontsize=12)
    axes[1].set(xticks=[0,1],xticklabels=names,ylim=(0,120),ylabel='Total validator principal removed (thousand ETH)',
                title='Same user exit credit; more operator bond returned')
    axes[1].title.set_fontsize(11)
    axes[1].legend(loc='upper right',fontsize=9,frameon=False)
    for ax in axes:
        ax.grid(axis='y',alpha=.2,zorder=0)
    fig.suptitle('The efficiency side of commission-first exits',fontsize=18,y=.985)
    fig.text(.5,.925,'50k rETH net shortfall · soonest sweep example versus all-random · matched ETH caps',ha='center',fontsize=11)
    fig.text(.015,.061,'All four commission rules leave about 10.64% weighted commission; the illustration uses the soonest sweep mean.',fontsize=9)
    fig.text(.015,.026,'Static contract-fee proxy, not a protocol APR forecast. Total validator principal includes operator bonds; it is not rETH TVL.',fontsize=9)
    fig.savefig(ROOT/'reth_efficiency.png',dpi=200)
    plt.close(fig)
    print('Created commission_clustering.png and reth_efficiency.png')


if __name__=='__main__':
    main()
