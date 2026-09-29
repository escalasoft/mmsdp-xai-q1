"""Publication plots from verified E2 CSV outputs only; isolated plotting runtime."""
import csv
import importlib.metadata
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'audits/q1-e2-final-closure/1.1.0'
CONFIGS=['C+P','C+T','P+T','C+P+T']
FAMILIES=['Logistic Regression','Random Forest','XGBoost','LightGBM']
MODS={'C':'CODE','P':'PROCESS','T':'TEXT'}
COLORS={'CODE':'#276494','PROCESS':'#BA6C1D','TEXT':'#487C5B'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                    'axes.spines.right':False,'svg.fonttype':'none','pdf.fonttype':42})


def read(name):
    with (OUT/'figure_data'/name).open() as stream:
        return list(csv.DictReader(stream))


def save(fig,name):
    path=OUT/'figures';path.mkdir(exist_ok=True)
    fig.savefig(path/(name+'.png'),dpi=300,facecolor='white')
    fig.savefig(path/(name+'.svg'),facecolor='white')
    fig.savefig(path/(name+'.pdf'),facecolor='white',metadata={'CreationDate':None,'ModDate':None})
    plt.close(fig)


def global_plot():
    rows=read('E2_global_modality_contributions.csv')
    fig,axes=plt.subplots(2,2,figsize=(12,8),sharex=True,sharey=True)
    maximum=max(float(r['mean_abs_phi']) for r in rows)
    plotted=[]
    for ax,config in zip(axes.flat,CONFIGS):
        mods=[MODS[m] for m in config.split('+')]
        offsets=np.linspace(-.23,.23,len(mods))
        for j,family in enumerate(FAMILIES):
            for offset,mod in zip(offsets,mods):
                values=np.array([float(r['mean_abs_phi']) for r in rows if r['configuration']==config
                                 and r['model_family']==family and r['modality']==mod])
                q1,median,q3=np.quantile(values,[.25,.5,.75])
                y=j+offset
                ax.plot([q1,q3],[y,y],color=COLORS[mod],linewidth=4,alpha=.35,solid_capstyle='butt')
                ax.scatter(values,np.full(len(values),y),s=17,color=COLORS[mod],alpha=.7,edgecolors='none')
                ax.scatter([median],[y],marker='D',s=27,color=COLORS[mod],edgecolors='white',linewidth=.5,zorder=4)
                plotted.append(dict(configuration=config,model_family=family,modality=mod,n_projects=len(values),
                                    q25_project_mean_abs=q1,median_project_mean_abs=median,q75_project_mean_abs=q3))
        ax.set_title(config,fontweight='bold',loc='left')
        ax.set_yticks(range(4),FAMILIES)
        ax.set_ylim(3.55,-.55)
        ax.set_xlim(0,maximum*1.08)
        ax.grid(axis='x',alpha=.2)
        ax.set_xlabel('Mean |contribution| within project (meta-logit units)')
    fig.suptitle('E2 • Modality contributions across projects and model families',fontsize=14,x=.04,ha='left',y=.98)
    handles=[Line2D([0],[0],marker='o',linestyle='',color=COLORS[m],label=m) for m in COLORS]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.55,.94),ncol=3,frameon=False)
    fig.text(.04,.025,'Each dot is one project; diamonds and thick segments show the across-project median and interquartile range.\n'
             'Historical OOF reference; fixed T1 foreground. Magnitude describes model behavior, not causal importance.',fontsize=9)
    fig.subplots_adjust(left=.16,right=.98,top=.85,bottom=.14,hspace=.38,wspace=.2)
    with (OUT/'figure_data/E2_global_plot_summary.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(plotted[0]));writer.writeheader();writer.writerows(plotted)
    save(fig,'E2_global_modality_contributions')


def local_plot():
    records={r['configuration']:r for r in read('E2_local_meta_logit_decomposition.csv')}
    fig,axes=plt.subplots(2,2,figsize=(12,8))
    for ax,config in zip(axes.flat,CONFIGS):
        r=records[config]
        mods=[MODS[m] for m in config.split('+')]
        values=[float(r['phi0'])]+[float(r[m+'_phi']) for m in mods]
        labels=['OOF baseline']+mods+['Meta-logit']
        current=0.
        positions=[]
        for i,value in enumerate(values):
            start=current;current+=value;positions.extend([start,current])
            color='#85929E' if i==0 else '#236DA0' if value>=0 else '#C25446'
            ax.bar(i,abs(value),bottom=min(start,current),width=.6,color=color,zorder=3)
            ax.plot([i+.3,i+.7],[current,current],color='#718096',linewidth=.8,linestyle='--')
            ax.annotate(f'{value:+.3f}',(i,max(start,current)),xytext=(0,5),textcoords='offset points',ha='center',fontsize=9)
        final=float(r['frozen_state_meta_logit']);i=len(values)
        ax.bar(i,abs(final),bottom=min(0,final),width=.6,color='#283848',zorder=3)
        ax.annotate(f'{final:+.3f}',(i,max(0,final)),xytext=(0,5),textcoords='offset points',ha='center',fontsize=9)
        positions.extend([0,final]);span=max(positions)-min(positions)
        ax.set_ylim(min(positions)-max(.2,span*.16),max(positions)+max(.35,span*.25))
        ax.axhline(0,color='#718096',linewidth=.7)
        ax.set_xticks(range(len(labels)),labels,fontsize=9)
        ax.set_ylabel('Fusion meta-logit')
        ax.grid(axis='y',alpha=.18,zorder=0)
        ax.set_title(f"{config}  |  {r['project'].replace('apache/','')} · {r['model_family']}\n"
                     f"Case {r['row_identifier'][:12]} · frozen RAW p = {float(r['frozen_RAW_probability']):.4f}",
                     loc='left',fontsize=10,pad=12)
    fig.suptitle('E2 • Frozen local cases: baseline + signed modality contributions',fontsize=14,x=.04,ha='left',y=.98)
    handles=[Line2D([0],[0],marker='s',linestyle='',color=c,label=label) for c,label in
             [('#85929E','OOF baseline'),('#236DA0','Positive movement'),('#C25446','Negative movement'),('#283848','Final meta-logit')]]
    fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.55,.94),ncol=4,frameon=False,fontsize=9)
    fig.text(.04,.025,'Fixed rule: local ordinal 1 in the lexicographically first eligible project/model scope for each configuration.\n'
             'Illustrations use no labels or explanation magnitudes for selection; axes vary by panel. Values are rounded only for display.',fontsize=9)
    fig.subplots_adjust(left=.08,right=.98,top=.82,bottom=.14,hspace=.48,wspace=.22)
    save(fig,'E2_local_meta_logit_decomposition')


if __name__=='__main__':
    global_plot();local_plot()
    (OUT/'plot_runtime.json').write_text(json.dumps(dict(python=platform.python_version(),
        packages={p:importlib.metadata.version(p) for p in ['matplotlib','numpy','pillow']},
        isolation='Temporary --target plotting packages; frozen predictive and XAI environments unchanged',
        input='Verified derived E2 CSV only; no frozen scientific source access'),indent=2)+'\n')
