from pathlib import Path
import json,html,sys
O=Path(__file__).resolve().parent;D=O/'data';F=Path(sys.argv[1]) if len(sys.argv)>1 else O/'figures';F.mkdir(exist_ok=True)
BLUE='#0072B2';ORANGE='#D55E00';INK='#182936';GRAY='#62717c';GREEN='#136f63'
def esc(s):return html.escape(str(s))
class SVG:
 def __init__(self,w,h):self.w=w;self.h=h;self.s=[f'<svg xmlns="http://www.w3.org/2000/svg" width="7.2in" height="{7.2*h/w:.4f}in" viewBox="0 0 {w} {h}"><rect width="100%" height="100%" fill="white"/>']
 def text(self,x,y,t,size=17,color=INK,weight='normal',anchor='start'):
  self.s.append(f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{esc(t)}</text>')
 def rect(self,x,y,w,h,fill,stroke='none'):self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" rx="3"/>')
 def line(self,x,y,x2,y2,col=GRAY):self.s.append(f'<line x1="{x}" y1="{y}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="1.2"/>')
 def save(self,n):(F/n).write_text('\n'.join(self.s+['</svg>']))
def bars(s,x,y,w,title,labels,vals,base,out,p,res):
 s.rect(x,y,w,475,'#f7f9fb');s.text(x+16,y+28,title,21,weight='bold')
 s.text(x+16,y+54,f'Base = {base:.6f} logit',16)
 s.text(x+16,y+77,'Signed contributions to the unimodal logit',15,color=GRAY)
 left=x+133;right=x+w-90;zero=(left+right)/2;half=(right-left)/2
 mx=max(abs(v) for v in vals)*1.08
 s.line(zero,y+92,zero,y+365,'#aeb8bf')
 for k,(lab,v) in enumerate(zip(labels,vals)):
  yy=y+109+k*31;xx=zero+v/mx*half
  s.text(x+15,yy+5,lab,16)
  s.rect(min(zero,xx),yy-12,max(abs(xx-zero),.7),20,ORANGE if v>0 else BLUE)
  s.text(x+w-12,yy+5,f'{v:+.4f}',15,anchor='end')
 s.text(x+16,y+397,f'Output = {out:.6f} logit',17,weight='bold')
 s.text(x+16,y+423,f'Unimodal RAW p = {p:.6f}',18,weight='bold')
 s.text(x+16,y+450,f'Additive residual = {abs(res):.2e}',15,color=GRAY)
def hierarchy(n):
 d=json.loads((D/f'figure_{n}.json').read_text());e=d['E2'];mods=['CODE','TEXT'] if n=='A' else ['CODE','PROCESS','TEXT'];s=SVG(1040,1010 if n=='A' else 1100)
 s.text(28,35,f'{n}  Linked explanations at two distinct levels',25,weight='bold')
 s.text(28,65,f'ActiveMQ / T1   •   LR   •   {d["configuration"]}   •   Frozen E1 local case 1',18)
 s.text(28,91,'Commit '+d['identity']['commit_identity'],16,color=GRAY)
 s.rect(28,110,984,290,'#f0f5f8');s.text(45,141,'E2  Modality contributions to the fusion meta-logit',21,weight='bold')
 s.text(45,168,'OOF reference   |   Separate additive decomposition',16,color=GRAY)
 vals=[float(e[m+'_phi']) for m in mods];base=float(e['phi0']);out=float(e['frozen_state_meta_logit']);lo=min([base,out]+[base+sum(vals[:i]) for i in range(len(vals)+1)])-.2;hi=max([base,out]+[base+sum(vals[:i]) for i in range(len(vals)+1)])+.2
 x0=270;x1=780;xp=lambda v:x0+(v-lo)/(hi-lo)*(x1-x0)
 s.text(46,198,f'Base = {base:.6f}',16)
 current=base
 for i,(m,v) in enumerate(zip(mods,vals)):
  y=223+i*33;s.text(46,y+5,m,17,weight='bold');s.text(140,y+5,f'p={float(e[m+"_probability"]):.6f}',15)
  end=current+v;s.rect(min(xp(current),xp(end)),y-12,max(abs(xp(end)-xp(current)),1),21,ORANGE if v>0 else BLUE)
  s.line(xp(current),y-17,xp(current),y+14);s.line(xp(end),y-17,xp(end),y+14)
  s.text(990,y+5,f'{v:+.6f}',16,anchor='end');current=end
 s.text(46,346,f'Fusion meta-logit = {out:.6f}   →   RAW p = {float(e["frozen_RAW_probability"]):.6f}',20,weight='bold')
 s.text(46,377,'Not a calibrated probability. Bar lengths use the E2 scale only.',16,color=GRAY)
 s.text(520,435,'↑  Unimodal probabilities are the verified E2 inputs  ↑',18,weight='bold',anchor='middle')
 c=d['CODE'];t=d['TEXT'];p=t['phi'];pos=sorted([i for i,v in enumerate(p) if v>0],key=lambda i:(-p[i],i))[:5];neg=sorted([i for i,v in enumerate(p) if v<0],key=lambda i:(p[i],i))[:2];keep=pos+neg
 labels=[t['features'][i] for i in keep]+[f'Other {len(p)-len(keep)}'];v=[p[i] for i in keep]+[sum(p[i] for i in range(len(p)) if i not in keep)]
 bars(s,28,458,482,'E1 CODE  •  LR analytical',c['features'],c['phi'],c['base'],c['output'],c['probability'],c['residual'])
 bars(s,530,458,482,'E1 TEXT  •  LR analytical',labels,v,t['base'],t['output'],t['probability'],t['residual'])
 s.text(28,965,'Orange: positive contribution. Blue: negative contribution. Not causal effects.',16)
 s.text(28,991,'No attribution is added or propagated between E1 and E2. Panel axes are independent.',16)
 if n=='D':
  s.rect(28,1010,984,67,'#fff3e5');s.text(43,1037,'PARTIAL — PROCESS is shown in E2 only.',18,weight='bold');s.text(43,1064,'E1 PROCESS not evaluated: temporal provenance not independently established',16)
 s.save(f'figure_{n}.svg')
def coverage():
 rows=json.loads((D/'figure_C.json').read_text());s=SVG(1040,865)
 s.text(28,37,'C  Explanatory coverage and verified connections',25,weight='bold');s.text(28,67,'ActiveMQ / T1   •   245 commits   •   Four model families',18)
 xs=[28,185,280,450,650,820];heads=['Modality','Model','E1 status','E2 input','E1–E2 link','Hierarchy']
 for x,t in zip(xs,heads):s.text(x,113,t,18,weight='bold')
 for k,r in enumerate(rows):
  y=132+k*43;s.rect(24,y-5,992,39,'#f7f9fb' if k%2==0 else '#ffffff');valid=r['E1_status']=='READY'
  values=[r['modality'],r['algorithm'],'READY' if valid else 'NO-GO¹' if r['modality']=='PROCESS' else 'NO-GO²','Available', 'Exact' if valid else 'Not available','READY branch' if valid else 'PARTIAL']
  for x,t in zip(xs,values):s.text(x,y+21,t,17,color=GREEN if t in ['Exact','READY','READY branch'] else INK)
 y=690
 for line in ['E2 is available in three configurations containing each modality.', '¹ PROCESS: temporal provenance not independently established.', '² RF TEXT: exact TreeSHAP additivity failure; no accepted E1 attributions.', 'NO-GO applies to E1; it does not mean zero predictive contribution.', 'Complete C+T links: LR / XGB / LGB. Configurations including PROCESS remain PARTIAL.']:
  s.text(28,y,line,16);y+=30
 s.save('figure_C.svg')
for n in ['A','D']:hierarchy(n)
coverage()
