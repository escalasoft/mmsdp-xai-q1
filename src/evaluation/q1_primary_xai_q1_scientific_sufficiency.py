"""Manuscript gate over frozen S56.2C audit outputs only; no artifact discovery."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'audits/q1-primary-xai-frozen-evidence-reuse/1.0.0'
OUT=BASE/'amendments/q1_scientific_sufficiency/1.0.0'
BRANCH='sprint-10/q1-primary-xai-execution'
TECH='PARTIAL_FROZEN_EVIDENCE_REUSE_FEASIBLE'
READY='Q1_XAI_INSUFFICIENT_FOR_PRIMARY_MANUSCRIPT_CLAIMS'
INCOMPLETE='Q1_INCOMPLETE_EVIDENCE'; NOT_DEFENSIBLE='Q1_NOT_DEFENSIBLE'
CLASSES=['Q1_SCIENTIFICALLY_SUFFICIENT','Q1_SCIENTIFICALLY_SUFFICIENT_WITH_LIMITATION',INCOMPLETE,NOT_DEFENSIBLE]
CRITERIA=[
 'Exact population provenance','Exact row identity','Exact partition provenance','Exact model-state linkage',
 'Exact preprocessing / feature-order linkage','No T2 exposure','No post-hoc model selection',
 'No post-hoc feature selection','No metric-driven XAI selection','Sufficient sample support for intended explanation',
 'Reproducible population-selection rule','Deterministic or explicitly governed explainer behavior',
 'Exact explainer output scale','Fidelity/additivity verification possible',
 'Project-level coverage appropriate for intended claim','Model-family coverage appropriate for intended claim',
 'Modality coverage appropriate for intended claim','Limitations do not invalidate central claim',
 'Auditable persisted evidence','Manuscript use requires no undocumented assumptions']
ZERO=['NEW_T1_SOURCE_ROW_READ_COUNT','T2_ACCESS_COUNT','T2_IDENTITY_READ_COUNT','T2_FEATURE_READ_COUNT','T2_LABEL_READ_COUNT',
 'MODEL_QUERY_COUNT','SHAP_EXECUTION_COUNT','ANALYTICAL_ATTRIBUTION_EXECUTION_COUNT','PREDICTIVE_METRIC_COUNT',
 'RETRAIN_COUNT','REFIT_COUNT','RECONSTRUCTION_COUNT','RECALIBRATION_COUNT','FIGURE_GENERATION_COUNT',
 'HISTORICAL_T1_ARTIFACT_READ_COUNT','FROZEN_SOURCE_ARTIFACT_PAYLOAD_READ_COUNT','DISCOVERY_RERUN_COUNT',
 'POPULATION_SELECTION_COUNT','COMMIT_COUNT','PUSH_COUNT']
READS=set()

def canonical(x):return (json.dumps(x,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name,x):(OUT/name).write_bytes(canonical(x))
def read(name):return json.loads((BASE/name).read_text())
def rows(name):return [json.loads(x) for x in (BASE/name).read_text().splitlines() if x.strip()]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

def guard(event,args):
 if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
 p=Path(os.fsdecode(args[0])).resolve()
 if not p.is_relative_to(ROOT):return
 mode,flags=args[1] or '',args[2] or 0
 writing=any(c in mode for c in 'wax+') or bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC))
 if writing and not p.is_relative_to(OUT):raise PermissionError('Amendment cannot write parent evidence or environment')
 allowed=(p.is_relative_to(OUT) or p.parent==BASE or p.suffix in ['.py','.pyc'] and p.is_relative_to(ROOT/'src')
  or p.suffix in ['.py','.pyc'] and p.is_relative_to(ROOT/'tests') or p.is_relative_to(ROOT/'.venv')
  or p==ROOT/'.gitignore' or p==ROOT/'pyproject.toml')
 if not allowed:raise PermissionError('Only base56.2C audit metadata permitted; no scientific artifact reopening')
 if not writing and p.parent==BASE:READS.add(p.name)

def verify_base():
 entries={n:h for h,n in (x.split('  ',1) for x in (BASE/'MANIFEST.sha256').read_text().splitlines())}
 assert all(Path(n).name==n for n in entries)
 assert set(entries)=={p.name for p in BASE.iterdir() if p.is_file() and p.name!='MANIFEST.sha256'}
 for n,h in entries.items():assert sha(BASE/n)==h,(n,'parent hash mismatch')
 return {'base_manifest_sha256':sha(BASE/'MANIFEST.sha256'),'files':entries,
  'nested_child_excluded_from_parent_manifest':True,'base_file_count_including_manifest':len(entries)+1,
  'technical_verdict':read('recommended_next_action.json')['outcome'],
  'base_source_module_sha256':sha(ROOT/'src/evaluation/q1_primary_xai_frozen_evidence_reuse.py'),
  'gitignore_sha256':sha(ROOT/'.gitignore')}

def classify_gate(checks,provenance=True):
 if not provenance:return NOT_DEFENSIBLE
 if len(checks)!=20 or any(x!='SUPPORTED' for x in checks):return INCOMPLETE
 return 'Q1_SCIENTIFICALLY_SUFFICIENT'

def make_profile(kind):
 supported={6,7,8,9,19}
 if kind=='E2':supported|={2,3,4,5,13}
 if kind=='E1':supported|={3,4}
 return {'profile_id':kind,'intended_use':'PRIMARY_EMPIRICAL_XAI_MANUSCRIPT_CLAIM',
  'criteria':[{'criterion_id':f'Q{i:02d}','criterion':name,
     'status':'SUPPORTED' if i in supported else 'NOT_ESTABLISHED_FOR_COMPLETE_PRIMARY_CLAIM',
     'basis':('Base frozen audit preserves boundaries, state/probability provenance and no-selection controls.' if i in supported
       else 'Partial components do not establish a complete governed population, explanation, fidelity and reporting chain.')} for i,name in enumerate(CRITERIA,1)],
  'interpretation':'SUPPORTED refers to this gate prerequisite, not support for an empirical claim. No imputed PASS for untested scale/determinism/fidelity.',
  'classification':INCOMPLETE}

def build():
 assert git('symbolic-ref','--short','HEAD')==BRANCH
 OUT.mkdir(parents=True,exist_ok=False);sys.addaudithook(guard)
 before=verify_base();assert before['technical_verdict']==TECH
 save('base_integrity_before.json',before)
 base_scope=read('scope_integrity.json');assert base_scope['count']==389
 e1=read('e1_family_feasibility.json');e2=read('e2_multimodal_feasibility.json')
 coverage=read('project_coverage_matrix.json')['projects'];projects=[r['project'] for r in coverage]
 families=[r['algorithm'] for r in e1['families']]
 scope_rows=read('row_identity_reconciliation.json')['T1'];assert len(scope_rows)==389
 candidates=rows('frozen_artifact_candidate_inventory.jsonl')
 configs={'C+P':56,'C+T':55,'P+T':55,'C+P+T':55}
 profiles={kind:make_profile(kind) for kind in ['E1','E2','ARTIFACT','AGGREGATE','GRAPH']}
 profiles['UNSAFE_OR_UNLINKED']={'profile_id':'UNSAFE_OR_UNLINKED','criteria':[{'criterion_id':f'Q{i:02d}','criterion':name,'status':'NOT_ESTABLISHED'} for i,name in enumerate(CRITERIA,1)],
  'classification':NOT_DEFENSIBLE,'interpretation':'Current use for a primary claim is not defensible; no allegation about historical artifact validity.'}
 save('q1_gate_criteria_and_profiles.json',{'criteria':CRITERIA,'profiles':profiles,'threshold_rule':'All20 supported for unqualified sufficiency; no numerical threshold invented for sample size or substantial coverage.',
  'limited_sufficiency_rule':'A narrowed empirical claim still needs complete evidence for its stated population, fidelity, scale and reproducibility. Raw input coverage alone is not a limitation-qualified result.',
  'no_partial_claim_marked_supported':True})
 ledger=[]
 def record(kind,identity,profile,reference,available,missing,extra=None):
  item={'unit_type':kind,'unit_id':identity,'gate_profile':profile,'criteria_count':20,
   'scientific_sufficiency':profiles[profile]['classification'],'claim_supported':False,
   'base_evidence_reference':reference,'base_evidence_sha256':before['files'][reference],
   'available_evidence':available,'missing_evidence':missing,
   'intended_use':'PRIMARY_Q1_XAI_CLAIM','technical_findings_preserved':True}
  item.update(extra or {});ledger.append(item)
 for r in candidates:
  unsafe=r['sufficiency'] in ['T2_CONTAMINATED_ARTIFACT','PROVENANCE_INSUFFICIENT'] or r.get('project_coverage_status')=='ZERO_CURRENT_APACHEJIT_COVERAGE'
  record('ARTIFACT',r['candidate_id'],'UNSAFE_OR_UNLINKED' if unsafe else 'ARTIFACT','frozen_artifact_candidate_inventory.jsonl',
   [r['type'],r['reason']],['No complete primary population-to-explanation chain established by this artifact alone.'],
   {'path':r['path'],'projects':r.get('projects',[]),'base_technical_classification':r['sufficiency'],
    'base_record_sha256':hashlib.sha256(canonical(r)).hexdigest(),'artifact_payload_reopened':False})
 for r in scope_rows:
  role='E2' if '+' in r['configuration'] else 'E1'
  record(role+'_SCOPE',r['model_identity_sha256'],role,'row_identity_reconciliation.json',
   ['Exact stored state linkage and T1 identity/probability correspondence.' if role=='E2' else 'Exact model states; T1 identities and probability records, not feature input vectors.'],
   ['Primary centered TRAIN-reference population unresolved; no primary fidelity/stability results.' if role=='E2' else 'T1 input representations and complete TRAIN feature reference absent; no primary explanations/fidelity/stability.'],
   {k:r[k] for k in ['project','algorithm','configuration','rows']})
 for r in coverage:
  record('PROJECT',r['project'],'AGGREGATE','project_coverage_matrix.json',[r],['No complete primary E1 or centered E2 scopes.'])
 for a in families:
  record('ALGORITHM_FAMILY',a,'AGGREGATE','e1_family_feasibility.json',['Final state and E2 raw input components exist.'],['No complete E1 or centered E2 result coverage.'])
 for m in ['CODE','PROCESS','TEXT']:
  record('E1_MODALITY',m,'E1','e1_modality_feasibility.json',['80 activemq TRAIN rows; stored model/preprocessing state.'],['No T1 feature inputs; no primary results.'])
 for config,n in configs.items():
  record('E2_CONFIGURATION',config,'E2','e2_multimodal_feasibility.json',[f'{n} exact raw T1 modality input sets.'],['Governed reference means, centered baseline, primary decomposition/fidelity and stability not complete.'])
 required_common=['Deterministically frozen TRAIN/T1 populations and exact identity/partition/model/representation provenance',
  'Governed scale and explainer with fidelity/additivity and sigmoid-linkage checks where applicable',
  'Stability/reliability and coverage-qualified reporting; auditable outputs, no cherry-picking']
 claims_data=[
 ('A','Feature-level patterns within CODE','C','E1 CODE T1 vectors and TRAIN reference','No T1 feature rows;80 TRAIN rows in one project'),
 ('B','Feature-level patterns within PROCESS','P','E1 PROCESS T1 vectors and TRAIN reference','No T1 feature rows;80 TRAIN rows in one project'),
 ('C','TEXT token/term attribution patterns','T','T1 raw text+frozen vectorizer or exact aligned TFIDF rows','Vocabulary/IDF exists, no T1 text/TFIDF rows'),
 ('D','Differences across model families','C/P/T and all fusion configurations','Comparable validated explanation scales/estimands for all eligible families','Four-family states/raw E2 inputs exist; complete explanations absent'),
 ('E','Cross-project explanatory stability','C/P/T and all fusion configurations','Governed repeat/stability evidence across eligible projects','Inputs/provenance across14projects, no primary repeated explanations'),
 ('F','Local explanation examples','C/P/T and E2','Predeclared deterministic local cases and complete case fidelity/baseline','T1 identities/labels/raw E2 inputs available; cases not selected, centered reference unresolved'),
 ('G','Multimodal modality contribution','C+P/C+T/P+T/C+P+T','Exact final-model probabilities and approved TRAIN means, alpha/beta, centered baseline and fidelity','221 raw input sets, incomplete centered reference'),
 ('H','Complementary modality behavior in full multimodality','C+P/C+T/P+T/C+P+T','Validated joint and pairwise explanation evidence across projects/families with limitations','55 full-multimodal raw input sets; no centered explanatory results'),
 ('I','Heterogeneity across projects','C/P/T and E2','Comparable project-wise distributions with coverage disclosed and contradictory results retained','14project raw E2 coverage; no validated primary explanatory distributions'),
 ('J','Calibration/XAI separation','E1/E2/E3','Explicit raw-vs-calibrated scale lineage and audited explanation/calibration mapping separation','Base audit records historical probability/state linkage; no primary explanation results'),
 ('K','Stability/reliability of explanations','C/P/T and E2','Frozen repeated attribution/stability outputs and fidelity for intended populations','No primary stability outputs; prior smoke validation cannot stand for campaign reliability')]
 claims=[]
 for cid,title,modalities,needed,available in claims_data:
  claims.append({'claim_id':cid,'planned_claim':title,'claim_type':'PRIMARY_EMPIRICAL_RESULT',
   'required_evidence':[needed,*required_common],'available_evidence':[available],
   'missing_evidence':['Complete primary explanation/fidelity/stability chain for this claim',needed],
   'project_coverage':{'eligible':14,'primary_validated':0,'raw_E2_component_projects':14,'TRAIN_feature_projects':1},
   'algorithm_coverage':{'eligible':families,'primary_validated':[]},'modality_coverage':modalities,
   'scientific_sufficiency_classification':INCOMPLETE,'claim_supported':False,
   'allowable_wording':('The reuse audit preserves raw/final probability provenance; calibration effects and primary explanations remain unassessed.' if cid=='J' else f'The audit identifies reusable components relevant to {title.lower()}; it does not establish this empirical finding.'),
   'prohibited_wording':f'The study establishes general {title.lower()} across the MMSDP-XAI campaign.',
   'references':['e1_modality_feasibility.json','e2_multimodal_feasibility.json','project_coverage_matrix.json','exact_missing_evidence.json']})
 save('q1_claim_to_evidence_matrix.json',{'claim_families':claims,'primary_supported_claim_count':0,
  'documentation_only':'The technical audit outcome and governance boundaries can be reported as methods/limitations; this is not an empirical XAI endpoint.',
  'no_causal_superiority_or_semantic_intent_claims':True})
 graphs=[]
 graph_names=['Global mean(|SHAP|) bar plot','Beeswarm plot','Local waterfall plot','TEXT attribution visualization',
  'Multimodal modality-contribution plot','Project heterogeneity heatmap','Algorithm-family comparison plot','Stability/reliability plot']
 for i,name in enumerate(graph_names,1):
  partial=i in [3,5,6,7]
  g={'graph_family':name,'required_evidence':required_common+['Complete appropriate E1 feature or E2 centered contribution inputs/results'],
    'evidence_completeness':'PARTIAL_COMPONENTS_ONLY' if partial else 'MISSING_PRIMARY_REPRESENTATION_OR_RESULTS',
    'sample_coverage':{'T1_identity_probability_rows_available':3787,'primary_explained_rows':0,'TRAIN_feature_smoke_rows':80},
    'project_coverage':{'raw_E2_inputs':14,'primary_publication_ready':0},
    'family_coverage':{'stored_components':families,'primary_publication_ready':[]},
    'modality_coverage':['C','P','T','C+P','C+T','P+T','C+P+T'],
    'baseline_definition':'E2 phi0=alpha+sum(beta_m*mu_m), reference unresolved; E1 frozen method-specific reference not materialized',
    'output_scale':'E2 meta-logit; E1 family-specific governed scale must be verified before comparable aggregation',
    'reproducibility_status':'Artifacts auditable; primary population/explanation reproduction not yet established',
    'fidelity_additivity_verification_availability':'Partial E2 raw algebra inputs exist; full primary centered/E1 audit unavailable',
    'interpretation_limits':['No unvalidated plot as primary result','No raw E2-only plot as complete E1/E2 campaign','No cross-project TEXT rank averaging','No causal or predictive superiority inference'],
    'Q1_sufficiency_classification':INCOMPLETE,'publication_ready':False,
    'allowable_manuscript_use':'NONE_AS_PRIMARY_EVIDENCE',
    'future_exploratory_designation':'EXPLORATORY_ONLY' if partial else 'NOT_READY',
    'future_exploratory_condition':'Requires separate authorization, valid baseline/case provenance and fidelity; no graph currently generated or recommended for publication.'}
  graphs.append(g)
  record('GRAPH',name,'GRAPH','xai_graphics_feasibility.json',[g['evidence_completeness']],['Primary publication chain incomplete.'])
 save('q1_graph_readiness_matrix.json',{'graphs':graphs,'primary_publication_ready_count':0,'exploratory_plots_count_as_primary':False})
 multimodal=[]
 for r in e2['scopes']:
  multimodal.append({'project':r['project'],'algorithm':r['algorithm'],'configuration':r['configuration'],
   'model_identity_sha256':r['model_identity_sha256'],'modality_order':r['exact_modality_order'],
   'quantities':{'alpha_and_beta':'STORED_EXACT_STATE_LINKAGE','p_C_p_P_p_T_configured_only':'STORED_T1_UNIMODAL_PROBABILITIES',
    'raw_fusion_logit':'DERIVABLE_FROM_STORED_INPUTS_NO_NEW_QUERY_NOT_EXECUTED',
    'sigmoid_probability_linkage':'STORED_PREDICTION_REFERENCE_EXISTS_FUTURE_FIDELITY_CHECK_REQUIRED',
    'mu_C_mu_P_mu_T_configured_only':'NOT_ESTABLISHED_FOR_FROZEN_PRIMARY_REFERENCE',
    'centered_baseline_phi0':'BLOCKED_BY_PRIMARY_MU_REFERENCE','centered_phi_m':'BLOCKED_BY_PRIMARY_MU_REFERENCE'},
   'raw_algebra_technical_readiness_preserved':r['uncentered_local_algebra_input_ready'],
   'scientific_sufficiency_classification':INCOMPLETE,'empirical_claim_supported':False,
   'missing':'Complete primary TRAIN reference provenance/selection and validation; stored OOF/smoke means are not interchangeable with final-model primary reference.'})
 save('q1_multimodal_explanation_readiness.json',{'configuration_counts':configs,'scopes':multimodal,
  'C_P_T_full_configuration_priority':True,'equations':{'eta_fusion':'alpha + sum(beta_m * p_m) over configured modalities',
   'phi_m':'beta_m * (p_m - mu_m)','phi_0':'alpha + sum(beta_m * mu_m)','probability':'sigmoid(eta_fusion)'},
  'TRAIN_mean_assessment':{'final_base_TRAIN_probability_vectors':168,'OOF_algorithm_project_matrices':56,
   'complete_primary_reference_mean_available_or_defensibly_derivable_now':False,
   'reason':'Final-base output arrays exist, but complete primary population linkage is unresolved. OOF excludes warmup and uses fold models; stored64-row activemq smoke reference uses another selection.',
   'no_mean_computed':True},
  'causal_importance_interpretation':'PROHIBITED','attribution_magnitude_superiority_claim':'PROHIBITED',
  'complete_Q1_multimodal_scope_count':0,'primary_multimodal_endpoint_sufficient':False})
 risks_text=['One algorithm presented as all four','One project presented as cross-project evidence','Feature importance presented as SHAP',
  'Fusion coefficients interpreted as causal modality importance','Incomparable TEXT token ranks averaged across projects',
  'Incomplete project coverage undisclosed','Post-hoc selected explanations presented as primary','Heterogeneous/contradictory explanations suppressed',
  'Anecdotal local cases used as global evidence','Only positive-looking examples used','Multimodal superiority claimed from attribution magnitude',
  'Causal defect mechanisms claimed from SHAP','Semantic intent claimed from TFIDF tokens','Insufficient E1 implies complete feature explainability',
  'E2-only evidence implies modality internals explained','Artifact used without exact provenance','Plot population not deterministically reconstructable']
 risks=[]
 for i,title in enumerate(risks_text,1):
  blocking=i in [6,14,15,16,17]
  risks.append({'risk_id':f'R{i:02d}','risk':title,'status':'PRESENT_BLOCKING' if blocking else 'CONTROLLED',
   'context':'Risk assessed against proposed primary manuscript use; not a claim that a figure or misconduct already occurred.',
   'basis':'Incomplete primary coverage, provenance/representation or population chain remains.' if blocking else 'No publication/selection performed; explicit claim restriction prevents promotion.',
   'control':'Block primary claims until exact missing chain is completed; disclose coverage and preserve contrary evidence.' if blocking else 'Predeclare cases and interpretation limits; retain all governed outputs; no causal/semantic/superiority claims.',
   'published_violation_observed':False})
 save('q1_risk_control_matrix.json',{'risks':risks,'blocking_risk_count':sum(x['status']=='PRESENT_BLOCKING' for x in risks),
  'blocking_risk_prevents_full_defensibility':True})
 required=[{'requirement_id':'REQ_E1','needed':'Exact governed E1 TRAIN reference inputs and T1 selected input representations for C/P/T, with full identity/model/preprocessing provenance. Raw TEXT+frozen vectorizer OR exact TFIDF rows accepted.',
   'why':'80 one-project TRAIN smoke rows and fitted vectorizers do not establish all-project feature explanations.'},
  {'requirement_id':'REQ_E2','needed':'Resolve exact primary TRAIN population and final-base probability linkage; predeclare any OOF/smoke alternative via separate review instead of substitution; recover auditable configured mu and centered baseline without undocumented assumptions.',
   'why':'All221 raw T1 input sets remain useful but do not complete centered multimodal endpoints.'},
  {'requirement_id':'REQ_SELECTION','needed':'Separately authorize and freeze deterministic background/foreground/local-case populations with coverage/sample rationale and exact manifests; no outcome-based selection.',
   'why':'A known selection rule is not evidence of a reproducible implemented primary population.'},
  {'requirement_id':'REQ_VALIDATION','needed':'After separate execution authorization, retain exact scales, outputs, additivity/fidelity/sigmoid and repeated stability checks for all intended eligible scopes.',
   'why':'TRAIN smoke checks and predictive G4/G5 equivalence do not establish primary explanation fidelity or stability.'},
  {'requirement_id':'REQ_REPORTING','needed':'Coverage-qualified project/family/configuration comparisons and heterogeneity; comparable feature semantics; traceable figures and local cases; no causal or semantic-intent claims.',
   'why':'General Q1 claims require the complete relevant endpoint chain, not visually complete sparse examples.'}]
 save('q1_exact_remaining_requirements.json',{'requirements':required,'no_new_metric_requirement':True,
  'no_T2_or_source_access_authorized':True,'no_extra_coverage_threshold_invented':True})
 save('q1_next_action.json',{'minimum_next_action':'Human review of a prospective evidence-completion plan that resolves BOTH E1 missing representations and E2 primary-reference semantics before any population freeze or primary execution.',
  'E2_only_alternative':'A separately predeclared narrowed E2 study could be reviewed after its complete reference/fidelity chain is established; it cannot represent complete primary MMSDP-XAI.',
  'recommended_priority':'Complete multimodal and feature-level evidence with exact provenance; do not prioritize obtaining plots.',
  'resume_population_freeze_authorized':False,'Sprint56_3_authorized':False,'model_query_authorized':False,
  'scientific_payload_read_authorized':False,'plots_authorized':False,'human_review_required':True})
 save('q1_scientific_sufficiency_ledger_summary.json',{'unit_counts':dict(Counter(x['unit_type'] for x in ledger)),
  'classification_counts':dict(Counter(x['scientific_sufficiency'] for x in ledger)),'primary_supported_units':0,
  'all389_scopes_assessed':True,'all_base_candidate_records_assessed':len(candidates),'technical_verdict':TECH})
 (OUT/'q1_scientific_sufficiency_ledger.jsonl').write_bytes(b''.join(canonical(x) for x in ledger))
 questions=[
 ('Is E1 CODE scientifically sufficient?','NO — T1 features and complete TRAIN input/reference chain absent.'),
 ('Is E1 PROCESS scientifically sufficient?','NO — same primary representation gap.'),
 ('Is E1 TEXT scientifically sufficient?','NO — T1 raw text/TFIDF rows absent; fitted vocabulary alone is insufficient.'),
 *[(f'Is E2 {c} scientifically sufficient?',f'NO — {n} raw input sets exist, but the governed centered primary reference/fidelity chain is incomplete.') for c,n in configs.items()],
 ('Are all four families adequately represented?','YES as stored technical components; NO as validated primary explanatory results.'),
 ('Is project coverage adequate?','14 projects have raw E2 components; primary validated explanatory coverage is0. General manuscript claims are not supported.'),
 *[(f'Are {label} publication-ready?','NO — no complete primary population/explanation/validation chain.') for label in ['global plots','beeswarm plots','local waterfall plots','TEXT attribution plots','multimodal contribution plots','heterogeneity plots','stability plots']],
 ('What exact evidence is missing?','REQ_E1,REQ_E2,REQ_SELECTION,REQ_VALIDATION,REQ_REPORTING; see q1_exact_remaining_requirements.json.'),
 ('Minimum next action?','Human review of a prospective plan completing E1 representations AND E2 reference semantics before population freeze/execution. No new execution authorization is implied.')]
 assert len(questions)==18
 save('q1_manuscript_xai_readiness.json',{'BASE_TECHNICAL_VERDICT':TECH,'Q1_XAI_MANUSCRIPT_READINESS':READY,
  'base_manifest_sha256':before['base_manifest_sha256'],'eligible_scopes':389,'E1_scopes':168,'E2_scopes':221,
  'excluded_scopes':base_scope['excluded'],'primary_Q1_sufficient_E1_scopes':0,'primary_Q1_sufficient_E2_scopes':0,
  'primary_supported_claim_families':0,'publication_ready_graph_families':0,
  'evidence_components_project_coverage':14,'evidence_components_algorithm_families':families,
  'why_not_defensible_with_limitations':'Missing central E1 and centered E2 endpoints invalidate full primary claims; broad raw component coverage cannot cure these gaps by narrowing wording alone.',
  'why_technical_partial_remains_valid':'Exact stored components remain useful for future governed work; no base finding is reclassified or weakened.',
  'explicit_answers':[{'question_number':i,'question':q,'answer':a} for i,(q,a) in enumerate(questions,1)]})
 base_counters=read('governance_counters.json')
 assert all(base_counters.get(k,0)==0 for k in ZERO if k not in ['HISTORICAL_T1_ARTIFACT_READ_COUNT'])
 save('governance_counters.json',{'amendment_counters':{k:0 for k in ZERO},
  'base_counter_snapshot':base_counters,'base_counter_file_sha256':before['files']['governance_counters.json'],
  'T2_STATE':'DENY_SEALED_REVIEWER_RESERVE','counter_scope':'Only already collected56.2C audit outputs read. No underlying row artifacts or models reopened.',
  'base_historical_T1_read_count_preserved':1,'Sprint56_3_authorized':False})
 finalize()

def manifest():
 (OUT/'MANIFEST.sha256').write_text(''.join(f'{sha(p)}  {p.name}\n' for p in sorted(OUT.iterdir()) if p.is_file() and p.name!='MANIFEST.sha256'))

def finalize():
 sys.addaudithook(guard)
 before=json.loads((OUT/'base_integrity_before.json').read_text());after=verify_base();assert before==after
 save('base_integrity_after.json',after)
 readiness=json.loads((OUT/'q1_manuscript_xai_readiness.json').read_text())
 checks=json.loads((OUT/'validation_results.json').read_text()) if (OUT/'validation_results.json').exists() else {'status':'PENDING'}
 report='# Q1 scientific sufficiency amendment to Sprint56.2C\n\n'+READY+'\n\n'
 report+='The base technical verdict remains **'+TECH+'**. This child assessment applies manuscript requirements to the already collected audit findings. It does not reopen scientific artifacts, repeat discovery or alter the technical findings.\n\n'
 report+=f'Branch: `{BRANCH}`. HEAD: `{git("rev-parse","HEAD")}`. Base manifest SHA256: `{before["base_manifest_sha256"]}`. All33 base files remain byte-identical; the nested amendment has its own manifest.\n\n'
 report+='## Scientific disposition\n\nNone of the168 E1 or221 E2 scopes meets the complete primary manuscript chain. CODE, PROCESS and TEXT E1 lack T1 inputs and sufficient governed TRAIN representations. E2 retains exact raw input components across14projects/four families, but its primary centered reference remains unresolved. These are central endpoint gaps, not minor coverage limitations. No empirical claim family or graph is marked supported/publication-ready.\n\n'
 report+='Raw uncentered E2 algebra remains technically reusable. It does not replace centered global analysis, explain modality internals or establish complementary/causal modality behavior. OOF and smoke references cannot silently substitute for the primary final-model TRAIN reference. The prospective equations are recorded without calculation.\n\n'
 report+='## Required answers\n\n'+'\n\n'.join(f'**{x["question_number"]}. {x["question"]}**\n\n{x["answer"]}' for x in readiness['explicit_answers'])
 report+='\n\n## Claim, graph and artifact traceability\n\nThe ledger assesses every base candidate artifact, all389 scopes,14 projects, four families, three E1 modalities, four E2 configurations and eight graph families. Each entry resolves to a20-criterion profile and hashed base evidence. The claim matrix covers A–K with required/available/missing evidence and allowed/prohibited wording. No partial empirical claim is marked supported. Methods-only reporting of audit status is distinct from an empirical XAI endpoint.\n\n'
 report+='All eight graph families are not publication-ready. Potential raw E2 exploratory graphics are marked EXPLORATORY_ONLY and are not recommended for publication or counted as primary evidence; they still require separate authorization and validation. Five blocking manuscript-use risks concern incomplete coverage, E1 completeness, E2-only generalization, provenance and reconstructable populations. Other listed risks remain controlled by explicit restrictions; no published violation is alleged.\n\n'
 report+='## Minimum next action\n\nReview a prospective plan that completes E1 representations and resolves E2 primary-reference semantics, then separately governs population selection, execution, fidelity/stability and coverage-qualified reporting. An E2-only narrowed study would require its own complete evidence chain and cannot substitute for the full primary MMSDP-XAI endpoints. No T2 access, metric recomputation or rapid plot-generation workaround is proposed.\n\n'
 report+='## Preservation and validation\n\nBase manifest and every base artifact match before/after. Base counters are copied unchanged; all amendment scientific access/execution counters are0, including historical T1 artifact reads. No models, raw row artifacts, plots, refitting or reconstruction are involved. No commit/push or branch change.\n\n'+json.dumps(checks,sort_keys=True)+'\n\n'
 report+='BASE_TECHNICAL_VERDICT =\n'+TECH+'\n\nQ1_XAI_MANUSCRIPT_READINESS =\n'+READY+'\n\nREADY FOR HUMAN REVIEW BEFORE NEXT PRIMARY XAI ACTION\n'
 (OUT/'Q1_SCIENTIFIC_SUFFICIENCY_REPORT.md').write_text(report)
 save('implementation_provenance.json',{'source_sha256':sha(Path(__file__)),'test_sha256':sha(ROOT/'tests/evaluation/test_q1_scientific_sufficiency.py') if (ROOT/'tests/evaluation/test_q1_scientific_sufficiency.py').exists() else None,
  'scientific_artifact_discovery_rerun':False,'underlying_payloads_read':False})
 prior=json.loads((OUT/'audit_metadata_access_log.json').read_text())['base_files_read'] if (OUT/'audit_metadata_access_log.json').exists() else []
 save('audit_metadata_access_log.json',{'base_files_read':sorted(READS|set(prior)),'underlying_artifact_reads':0})
 manifest();print(READY)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['build','finalize','manifest'])
 {'build':build,'finalize':finalize,'manifest':manifest}[parser.parse_args().stage]()
