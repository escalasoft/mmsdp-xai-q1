"""Deterministic SVG scientific plots from persisted figure data only."""
import json,sys,math,html
from pathlib import Path
B=Path(__file__).resolve().parent
DATA=Path(sys.argv[1]) if len(sys.argv)>1 else B/'tables/figure_data'
OUT=Path(sys.argv[2]) if len(sys.argv)>2 else B/'figures'
OUT.mkdir(exist_ok=False)
BLUE='#2878A5';ORANGE='#CA623C';INK='#203345';GRAY='#637381';LIGHT='#E4E9ED'
class SVG:
 def __init__(self,w,h,title,desc):
  self.w=w;self.h=h;self.s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img"><title>{html.escape(title)}</title><desc>{html.escape(desc)}</desc><rect width="100%" height="100%" fill="white"/>']
 def text(self,x,y,t,size=16,color=INK,anchor='start',weight='normal'):
  self.s.append(f'<text x="{x:.3f}" y="{y:.3f}" font-family="Arial,Helvetica,sans-serif" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{html.escape(str(t))}</text>')
 def line(self,x,y,x2,y2,color=LIGHT,width=1,dash=''):
  self.s.append(f'<line x1="{x:.3f}" y1="{y:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"/>')
 def rect(self,x,y,w,h,fill):self.s.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{max(w,.4):.3f}" height="{h:.3f}" fill="{fill}"/>')
 def circle(self,x,y,r,fill,opacity=.4):self.s.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r}" fill="{fill}" opacity="{opacity}"/>')
 def finish(self,name):
  (OUT/(name+'.svg')).write_text(''.join(self.s)+'</svg>')
def load(name):return json.loads((DATA/(name+'.json')).read_text())
def fmt(x):return f'{x:.3g}'
def axis(s,x,y,w,lo,hi,label,ticks=4):
 for k in range(ticks+1):
  v=lo+(hi-lo)*k/ticks;xx=x+w*k/ticks;s.line(xx,y,xx,y+5,GRAY);s.text(xx,y+24,fmt(v),14,GRAY,'middle')
 s.line(x,y,x+w,y,GRAY);s.text(x+w/2,y+52,label,15,INK,'middle')
def global_plot():
 d=load('global_importance');s=SVG(1220,900,'Global CODE attribution importance','Within-model mean absolute attribution, 245 commits; independent horizontal scales.')
 s.text(35,38,'Global CODE attribution importance',25,weight='bold');s.text(35,65,'ActiveMQ / T1 · 245 commits · six features · independent panel scales',16,color=GRAY)
 for n,(m,obj) in enumerate(d['models'].items()):
  col=n%2;row=n//2;xx=60+col*600;yy=115+row*360;values=obj['values'];order=sorted(range(6),key=lambda j:(-values[j],d['features'][j]));mx=max(values)*1.25
  s.text(xx,yy,m,22,weight='bold');s.text(xx+60,yy,obj['scale'],15,color=GRAY)
  x=xx+45;w=440
  for k,j in enumerate(order):
   y=yy+25+k*37;s.text(x-12,y+20,d['features'][j],17,anchor='end');width=values[j]/mx*w;s.rect(x,y,width,25,BLUE);s.text(x+width+8,y+19,fmt(values[j]),14)
  axis(s,x,yy+255,w,0,mx,'Mean absolute attribution')
 s.text(35,865,'Bars are not comparable in magnitude across output scales. No causal interpretation.',15,color=GRAY);s.finish('global_importance')
def distributions():
 d=load('attribution_distributions');s=SVG(1220,960,'CODE attribution distributions','All 245 commits shown per feature. Point color indicates attribution sign, not feature value.')
 s.text(35,38,'CODE attribution distributions',25,weight='bold');s.text(35,65,'Each point is one commit; color denotes contribution sign, not original feature value.',16,color=GRAY)
 for n,(m,obj) in enumerate(d['models'].items()):
  xx=60+(n%2)*600;yy=115+(n//2)*390;s.text(xx,yy,m,22,weight='bold');s.text(xx+60,yy,obj['scale'],15,color=GRAY)
  a=obj['values'];lo=min(min(r) for r in a);hi=max(max(r) for r in a);pad=(hi-lo)*.07;lo-=pad;hi+=pad;x=xx+45;w=440
  tx=lambda v:x+(v-lo)/(hi-lo)*w
  s.line(tx(0),yy+15,tx(0),yy+260,GRAY,1,'3 3')
  for j,f in enumerate(d['features']):
   y=yy+40+j*40;s.text(x-12,y+5,f,17,anchor='end');s.line(x,y,x+w,y,LIGHT,.7)
   vals=sorted(r[j] for r in a);median=vals[len(vals)//2]
   for i,r in enumerate(a):
    jitter=12*math.sin((i+1)*12.9898+(j+1)*78.233);s.circle(tx(r[j]),y+jitter,2.3,ORANGE if r[j]>0 else BLUE,.4)
   s.line(tx(median),y-14,tx(median),y+14,INK,2)
  axis(s,x,yy+270,w,lo,hi,'Signed attribution')
 s.text(35,925,'Deterministic vertical jitter separates points; black ticks mark medians. All observations retained.',15,color=GRAY);s.finish('attribution_distributions')
def rankings():
 d=load('rank_comparison');s=SVG(1020,520,'Within-model feature rankings','Rank one is highest mean absolute attribution; ranks do not equate model output scales.')
 s.text(40,40,'Within-model feature rankings',25,weight='bold');s.text(40,70,'Ranked by mean absolute attribution · rank 1 = largest · no cross-scale magnitude comparison',16,color=GRAY)
 colors=['#205B7B','#397B9A','#679BB2','#96B9C8','#C4D8DF','#E6EEF1']
 for j,f in enumerate(d['features']):s.text(220+j*125,120,f,20,anchor='middle')
 for i,(m,rr) in enumerate(d['models'].items()):
  y=145+i*70;s.text(95,y+37,m,21,weight='bold')
  for j,r in enumerate(rr):s.rect(163+j*125,y,114,57,colors[r-1]);s.text(220+j*125,y+37,r,23,'white' if r<=2 else INK,'middle','bold')
 s.text(40,475,'Descriptive comparison across six aligned features; no hypothesis test or generalization claim.',15,color=GRAY);s.finish('rank_comparison')
def waterfalls(m):
 d=load('waterfalls_'+m);s=SVG(1500,2240,f'{m}: eight frozen local explanations','Waterfall decompositions of the eight preselected commits. Positive orange; negative blue. All six features shown.')
 s.text(40,42,f'{m}: eight frozen local explanations',27,weight='bold');s.text(40,72,d['scale']+' · orange: positive contribution · blue: negative contribution',18,color=GRAY)
 for n,r in enumerate(d['cases']):
  xx=45+(n%2)*750;yy=130+(n//2)*515;phi=r['phi'];order=sorted(range(6),key=lambda j:(-abs(phi[j]),d['features'][j]));seq=[r['base']]
  for j in order:seq.append(seq[-1]+phi[j])
  lo=min(seq+[0.]);hi=max(seq+[0.]);pad=max((hi-lo)*.15,1e-5);lo-=pad;hi+=pad;x=xx+55;w=510;tx=lambda v:x+(v-lo)/(hi-lo)*w
  s.text(xx,yy,f"Case {r['local_index']+1} · {r['commit_identity'][:12]}",19,weight='bold')
  s.text(xx,yy+26,f"Stored p(defect) = {r['probability']:.4f} · residual = {r['residual']:.2g}",15,color=GRAY)
  s.text(xx,yy+54,f"Base = {r['base']:.5g}    Reconstructed output = {r['reconstructed']:.5g}",15)
  s.line(tx(0),yy+73,tx(0),yy+340,GRAY,1,'3 3')
  for k,j in enumerate(order):
   y=yy+88+k*39;left=min(seq[k],seq[k+1]);right=max(seq[k],seq[k+1]);s.text(x-12,y+19,d['features'][j],17,anchor='end');s.rect(tx(left),y,tx(right)-tx(left),26,ORANGE if phi[j]>=0 else BLUE)
   # Values outside the plotting region avoid collisions with short or long bars.
   s.text(x+w+12,y+19,f'{phi[j]:+.3g}',14)
   if k<5:s.line(tx(seq[k+1]),y+26,tx(seq[k+1]),y+39,GRAY,1,'2 2')
  s.line(tx(seq[-1]),yy+327,tx(seq[-1]),yy+344,INK,3);axis(s,x,yy+350,w,lo,hi,'Cumulative model output')
 s.text(40,2205,'Feature values were not persisted; labels identify contributions only. Local cases were fixed before attribution.',17,color=GRAY);s.finish('waterfalls_'+m)
global_plot();distributions();rankings()
for m in ['LR','RF','XGB','LGB']:waterfalls(m)
print('Seven SVG figures generated, including 32 local waterfall panels.')
