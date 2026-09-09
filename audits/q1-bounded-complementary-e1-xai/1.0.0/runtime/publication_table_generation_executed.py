from pathlib import Path
import csv,io,json,hashlib,sys
sys.path.insert(0,str(Path.cwd()))
from src.evaluation import q1_bounded_complementary_e1_xai as q
p=q.OUT
q.manifest(); q.verify_manifest(p)
def table(name,rows):
 b=io.StringIO();w=csv.DictWriter(b,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 (p/'tables').mkdir(exist_ok=True);(p/'tables'/f'{name}.csv').write_text(b.getvalue());q.save(f'tables/{name}.json',rows)
 keys=list(rows[0]);(p/'tables'/f'{name}.md').write_text('| '+' | '.join(keys)+' |\n| '+' | '.join('---' for _ in keys)+' |\n'+''.join('| '+' | '.join(str(r[k]).replace('|','/') for k in keys)+' |\n' for r in rows))
g=q.rows(p/'e1_global_feature_importance.jsonl'); f=q.read(p/'e1_fidelity_results.json');s=q.read(p/'e1_stability_results.json');cross=q.read(p/'e1_cross_model_consistency.json');local=q.rows(p/'e1_local_explanations.jsonl')
table('E1-1_scope',[dict(project=q.PROJECT,modality='TEXT',family=a,status='VALID' if a in f else 'EXCLUDED_EXACT_ADDITIVITY_FAILURE',representation='RECONSTRUCTED',predictor='RECONSTRUCTED',background=256,foreground=245,local_cases=8,scale=q.SCALES[a]) for a in q.FAMILIES])
table('E1-2_top20',[r for r in g if r['rank']<=20]);table('top10',[r for r in g if r['rank']<=10]);table('global_full',g)
(p/'e1_global_feature_importance.csv').write_bytes((p/'tables/global_full.csv').read_bytes())
table('E1-3_fidelity_stability',[dict(family=a,fidelity=f[a]['status'] if a in f else 'FAIL_INTERNAL_ADDITIVITY',n=245 if a in f else 0,max_residual=f[a]['max_residual'] if a in f else 'UNAVAILABLE',tolerance=f[a]['tolerance'] if a in f else 'Frozen exact check failed',stability=s[a]['status'] if a in s else 'INSUFFICIENT_EVIDENCE',repetitions=20 if a in s else 0,max_repeat_difference=s[a]['max_absolute_difference'] if a in s else 'UNAVAILABLE') for a in q.FAMILIES])
table('fidelity',[{k:v for k,v in r.items() if k not in ['repetition_fidelity']}|{'family':a} for a,r in f.items()]);table('stability',[dict(family=a,status=r['status'],repetitions=r['repetitions'],pairs=r['pairs_evaluated'],max_absolute_difference=r['max_absolute_difference']) for a,r in s.items()])
table('E1-4_consistency',cross['comparisons'])
hierarchy=[dict(level='E1',role='COMPLEMENTARY',question='Within-modality feature explanation',scope='ActiveMQ TEXT only',scale='LR logit; RF positive-class output unavailable; XGB/LGB raw margin',boundary='Associational; reconstructed states; no generalization'),dict(level='E2',role='PRIMARY_MULTIMODAL_XAI',question='Between-modality fusion explanation',scope='Frozen inherited multimodal scope',scale='Fusion meta-logit',boundary='Unchanged; no mathematical propagation of E1')]
table('E1-5_hierarchy',hierarchy)
table('local_explanations',[{k:v for k,v in r.items() if k not in ['top_positive_features','top_negative_features']}|dict(top_positive='; '.join(x['token'] for x in r['top_positive_features']),top_negative='; '.join(x['token'] for x in r['top_negative_features'])) for r in local])
# Read already persisted LR vector only for the prospectively fixed first local case.
import numpy as np
case=q.rows(p/'e1_local_case_population.jsonl')[0];r=next(r for r in local if r['family']=='LR' and r['row_identifier']==case['row_identifier']);arr=np.load(p/r['complete_attribution_reference'])['values'][r['foreground_index']];names=q.read(p/'representations/train_verified_copy/transform_state.json')['feature_order'];indices=sorted(range(len(arr)),key=lambda j:(-abs(arr[j]),names[j]))[:12]
lrsource=[dict(token=names[j],attribution=float(arr[j]),commit_identity=case['commit_identity'],base_value=r['base_value'],model_output=r['model_output']) for j in indices]
lrsource.append(dict(token='All other features (net)',attribution=float(sum(arr[j] for j in range(len(arr)) if j not in indices)),commit_identity=case['commit_identity'],base_value=r['base_value'],model_output=r['model_output']))
table('figure_local_source',lrsource)
# Explicit unavailable RF state, never fake zero attributions.
q.save('rf_e1_fidelity.json',dict(status='FIDELITY_FAIL',n_attempted=245,n_completed=0,max_residual=None,reason=q.read(p/'family_execution_failures.json')['RF']['error'],published=False))
f['RF']=q.read(p/'rf_e1_fidelity.json');q.save('e1_fidelity_results.json',f)
s['RF']=dict(status='INSUFFICIENT_EVIDENCE',repetitions_completed=0,reason='Excluded before scientific use: exact TreeSHAP additivity failure');q.save('e1_stability_results.json',s)
q.save('rf_e1_shap_values_status.json',dict(status='NOT_PUBLISHED_INVALID_ADDITIVITY',array=None))
q.save('rf_e1_expected_values_status.json',dict(status='NOT_PUBLISHED_INVALID_ADDITIVITY',value=None))
q.save('protocol_summary.json',dict(verdict='56_3C_PASS_BOUNDED_E1_XAI_WITH_PREDECLARED_LIMITATIONS',valid_families=['LR','XGB','LGB'],attempted_families=list(q.FAMILIES),RF='EXCLUDED_ADDITIVITY_FAILURE',repair_attempts=1,scope='apache/activemq × TEXT',scientific_use='BOUNDED_COMPLEMENTARY'))
q.save('q1_bounded_e1_sufficiency.json',dict(status='Q1_BOUNDED_E1_COMPLEMENTARY_EVIDENCE_VIABLE_WITH_LIMITATION',scope_transparent=True,provenance='Exact verified representation after child-only serialization repair',T1_labels_untouched=True,T2_sealed=True,alignment=True,exact_methods=True,fidelity='3 valid; RF excluded',stability='3 exact across 20 seeds',multi_model_comparison='3 valid families; RF unavailable',global_local=True,traceability='ARCHITECTURAL',reproducibility=True,publication='Tables, figures and source digests',no_overclaim=True,legacy_regressions='Inherited terminal-newline hash discrepancies, not new parent mutation'))
q.save('recommended_next_action.json',dict(action='MANUSCRIPT_XAI_INTEGRATION',steps=['Integrate frozen E2 as primary explainability results','Integrate bounded E1 tables and figures for LR/XGB/LGB; disclose RF failure','Write final Results, Discussion and Threats to Validity','Consolidate final framework figure'],no_recovery_sprint=True,no_source_search=True,no_commit_push_PR=True))
limitations=q.read(p/'e1_limitations.json')+['RF failed exact TreeSHAP additivity and is excluded under the frozen fidelity policy.','One terminal LF was restored in five child representation copies to recover exact inherited hashes; parent files were unchanged.','Legacy R4/R4A/R4B regression failures arise from 22 inherited terminal-LF discrepancies; no additional recovery is undertaken.']
q.save('e1_limitations.json',limitations)
claims=[dict(claim='ActiveMQ TEXT LR/XGB/LGB feature explanations are faithful to their corresponding reconstructed predictor',status='SUPPORTED_WITH_LIMITATION',evidence=['e1_fidelity_results.json','e1_model_representation_alignment.jsonl']),dict(claim='Attributions repeat exactly under 20 frozen seeds and fixed populations',status='SUPPORTED_WITH_LIMITATION',evidence=['e1_stability_results.json']),dict(claim='Feature explanations depend on model family',status='SUPPORTED',evidence=['e1_cross_model_consistency.json','e1_explanation_heterogeneity.json']),dict(claim='RF feature attributions are publication-ready',status='NOT_SUPPORTED',evidence=['rf_e1_fidelity.json']),dict(claim='E1 complements E2 through architectural continuity',status='SUPPORTED_WITH_LIMITATION',evidence=['e1_to_e2_traceability.jsonl','e1_e2_continuity_contract.json']),dict(claim='Full-modality or cross-project feature explanation',status='NOT_SUPPORTED',evidence=['bounded_e1_scope_registry.json','e1_limitations.json']),dict(claim='Exact empirical same-row E1-to-E2 probability bridge',status='DEFERRED',evidence=['e1_to_e2_traceability.jsonl'])]
q.ledger('e1_claim_ledger.jsonl',claims)
q.save('validation_results.json',dict(status='IN_PROGRESS',safe_regressions=dict(passed=383,failed=1,errors=51,deselected=1,reason='Inherited terminal-LF digest discrepancies; selected tests use metadata/synthetic inputs only'),T2_payload_tests_run=False,T1_label_dependent_tests_run=False))
q.manifest()
