"""Explicitly post-hoc analysis; does not alter frozen experiment or predictions."""
import gzip,json,sys
from collections import Counter,defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
import model,checker
cases={c['id']:c for c in json.loads((ROOT/'cases.json').read_text())}
groups=[json.loads(x) for x in (ROOT/'results-v1/group-summaries.jsonl').read_text().splitlines()]
condition=[]
for g in groups:
 c=cases[g['case_id']]
 if g['policy']=='horizon_aware' and c['observation']=='certified' and c['retry_outcome']!='reject' and c['budget']>=3 and c['deadline']>=c['original_terminal']+c['lag']+1:
  condition.append(g)
boundary=dict(label='Post-hoc conditional completion boundary, not a preregistered superiority test',
 condition='certified status; successful or timeout-committing retry; budget >= 3; action deadline >= original_terminal + lag + 1; frozen horizon drains all pending effects',
 cases=len(condition),terminal_paths=sum(g['paths'] for g in condition),all_paths_actual_complete=all(g['actual_complete_paths']==g['paths'] for g in condition),
 scope='Finite enumerated cases; analytic argument is bounded by the frozen service semantics.')
paired=defaultdict(dict)
for g in groups:paired[g['case_id']][g['policy']]=g
comparison=Counter()
for p in paired.values():
 b=p['capability_fallback'];h=p['horizon_aware']
 comparison['horizon_lower_worst_call_envelope']+=h['max_calls']<b['max_calls']
 comparison['horizon_higher_worst_call_envelope']+=h['max_calls']>b['max_calls']
 comparison['same_worst_call_envelope']+=h['max_calls']==b['max_calls']
 comparison['horizon_strictly_slower_all_orders']+=h['min_return']>b['max_return']
 comparison['baseline_strictly_slower_all_orders']+=b['min_return']>h['max_return']
 comparison['horizon_guaranteed_justification_loss']+=(b['justified_complete_paths']==b['paths'] and h['justified_complete_paths']<h['paths'])
 comparison['horizon_possible_completion_gain']+=(h['actual_complete_paths']>0 and b['actual_complete_paths']==0)
analysis=dict(boundary=boundary,comparisons=dict(comparison),comparison_warning='Same exogenous case and budget; different policy-induced scheduler trees, so ranges are not paired path estimates.')
(ROOT/'supplementary/boundary-analysis.json').write_text(json.dumps(analysis,indent=2,sort_keys=True)+'\n')
base=dict(id='posthoc-never',family='supplementary_not_in_frozen_manifest',originals=['early','never'],late=3,original_terminal=4,
 scope='item',strategy='reserve',ttl=2,observation='unavailable',lag=0,retry_outcome='success',budget=3,deadline=10,horizon=15)
other=dict(base,id='posthoc-late',originals=['early','late'])
pair=dict(label='Post-hoc two-world probe under unchanged frozen semantics; not counted among 800 cases',worlds=[base,other],
 shared_public_contract=model.initial_view(base)==model.initial_view(other),results={})
for policy in ['horizon_aware','blind_keyed']:
 left=model.simulate(base,policy);right=model.simulate(other,policy)
 pair['results'][policy]=dict(left=left,right=right,left_coverage=checker.validate_group(left),right_coverage=checker.validate_group(right),
  public_trace_sets_identical={json.dumps(r['public_trace'],sort_keys=True) for r in left}=={json.dumps(r['public_trace'],sort_keys=True) for r in right})
(ROOT/'supplementary/indistinguishability-pair.json').write_text(json.dumps(pair,indent=2,sort_keys=True)+'\n')
with gzip.open(ROOT/'results-v1/rows.jsonl.gz','rt') as f:
 for line in f:
  r=json.loads(line);c=r['case']
  if c['family']=='expiry_late_original' and c['late']==8 and c['scope']=='item' and c['strategy']=='reserve' and c['ttl']==2 and c['originals']==['early','late'] and c['retry_outcome']=='timeout_commit' and r['policy']=='blind_keyed' and r['metrics']['post_return_duplicate_effects']:
   (ROOT/'supplementary/composed-post-return-counterexample.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n');break
print(json.dumps(analysis,indent=2,sort_keys=True))
print('TWO_WORLD_PUBLIC_CONTRACT_EQUAL',pair['shared_public_contract'])
for p,v in pair['results'].items():print(p,'same_public_trace_sets',v['public_trace_sets_identical'],'left_counts',v['left'][0]['metrics']['counts'],'right_counts',v['right'][0]['metrics']['counts'])
