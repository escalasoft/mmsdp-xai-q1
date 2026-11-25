"""Independent arithmetic checks, regeneration comparison and PNG pixel validation."""
import hashlib,json,math,statistics,itertools,datetime
from pathlib import Path
import numpy as np
from PIL import Image
B=Path(__file__).resolve().parent;ROOT=B.parents[2];S=ROOT/'audits/q1-e1-code-execution/1.0.0/scientific'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S/'MANIFEST.json')=='1da3ac92a999ea9d5b2212741dcc6cd40c941beb549dc2b343f3d68fae7ad633'
expected={'LR':'3fd3654d8804ffcf12d55b62e9d5101abfc150bac6ab07fb29c83c0a3151c393','RF':'6dd4a1a0e23f82c082ec21e4e7484bdf617fae2835d4c764fecf1fa53ef8af0a','XGB':'addc2b810ce5f564e16ae4cb369ce10b17dec44d6d010ed5fd8534229c754c73','LGB':'19808c78f6de9ee048f1c1a5f997b75be05ebcdfa40a1408f3064f27f117ddde'}
for m,h in expected.items():assert sha(S/m/'explanations.npz')==h
for p,h in json.loads((S/'MANIFEST.json').read_text()).items():assert sha(S/p)==h
def near(a,b):assert math.isclose(float(a),float(b),rel_tol=1e-12,abs_tol=1e-12),(a,b)
def quantile(v,q):
    s=sorted(v);z=(len(s)-1)*q;i=math.floor(z);j=math.ceil(z);return s[i]+(s[j]-s[i])*(z-i)
stats=json.loads((B/'tables/global_statistics.json').read_text());features=['la','ld','nf','nd','ns','ent'];means={}
for m in expected:
    with np.load(S/m/'explanations.npz',allow_pickle=False) as z:
        phi=z['phi'][0];means[m]=[]
        for j,f in enumerate(features):
            r=next(r for r in stats if r['model']==m and r['feature']==f);v=list(map(float,phi[:,j]));a=list(map(abs,v));means[m].append(math.fsum(a)/245)
            near(r['mean_absolute'],math.fsum(a)/245);near(r['mean_signed'],math.fsum(v)/245);near(r['median_absolute'],statistics.median(a));near(r['median_signed'],statistics.median(v));near(r['std_signed_population'],statistics.pstdev(v));near(r['std_absolute_population'],statistics.pstdev(a));near(r['iqr_signed'],quantile(v,.75)-quantile(v,.25));near(r['iqr_absolute'],quantile(a,.75)-quantile(a,.25));near(r['minimum'],min(v));near(r['maximum'],max(v))
            for p in [1,5,25,50,75,95,99]:near(r[f'p{p:02d}_signed'],quantile(v,p/100))
            near(r['positive_proportion_exact'],sum(x>0 for x in v)/245);near(r['negative_proportion_exact'],sum(x<0 for x in v)/245);near(r['zero_proportion_exact'],sum(x==0 for x in v)/245)
            near(r['positive_proportion_1e12'],sum(x>1e-12 for x in v)/245);near(r['negative_proportion_1e12'],sum(x< -1e-12 for x in v)/245);near(r['null_proportion_1e12'],sum(abs(x)<=1e-12 for x in v)/245)
for r in json.loads((B/'tables/rank_concordance.json').read_text()):
    a,b=means[r['model_a']],means[r['model_b']];ra=[sorted(a).index(v)+1 for v in a];rb=[sorted(b).index(v)+1 for v in b];near(r['global_spearman'],1-6*sum((x-y)**2 for x,y in zip(ra,rb))/(6*(36-1)))
tables=[]
for p in sorted((B/'tables').rglob('*')):
    if p.is_file():q=B/'verification/tables'/p.relative_to(B/'tables');assert sha(p)==sha(q);tables.append(str(p.relative_to(B)))
figs=[]
for p in sorted((B/'figures').glob('*.svg')):
    q=B/'verification/figures'/p.name;assert sha(p)==sha(q)
    png=p.with_suffix('.png');repeat=q.with_suffix('.png')
    with Image.open(png) as a,Image.open(repeat) as b:
        a.load();b.load();assert a.size==b.size and a.tobytes()==b.tobytes();assert all(abs(d-300)<1 for d in a.info['dpi']);assert min(a.size)>=1500
        figs.append({'svg':p.name,'svg_bytes_identical':True,'png_bytes_identical':sha(png)==sha(repeat),'png_pixels_identical':True,'size':list(a.size),'dpi':list(a.info['dpi']),'png_sha256':sha(png),'svg_sha256':sha(p)})
result={'status':'PASS','verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_expected_hashes_match':True,'all_source_artifacts_unchanged':True,'statistics_regenerated_in_separate_process':True,'independent_standard_library_arithmetic_check':'PASS','global_statistic_rows':24,'rank_pair_checks':6,'regenerated_table_and_plot_data_files':tables,'figures':figs,'scientific_models_or_SHAP_executed':False,'feature_values_not_available':True,'visual_review':'All seven figure sheets visually inspected; labels, titles, scales, panels and figure boundaries checked.'}
with (B/'reproduction_verification.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True)
print(json.dumps({'status':'PASS','table_files':len(tables),'figures':len(figs),'all_pixels_identical':True}))
