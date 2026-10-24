"""Bounded exact enumeration. Standard library only. Never edits source corpus."""
import copy, gzip, hashlib, itertools, json, time
from collections import Counter
from pathlib import Path
from vendor import model, checker
import policies
from test_boundary import CASE
ROOT=Path(__file__).resolve().parent
PINS={'model.py':'7379f9464a8b00b68cca1b7cbce67d453335b5315be2959b9c2b85d2fc043766','checker.py':'9751e07387d849ca8b99592ff7b655235d8596a226a06bd92a38095a7e5b8665'}
for name,sha in PINS.items():assert hashlib.sha256((ROOT/'vendor'/name).read_bytes()).hexdigest()==sha
BOUNDS=dict(per_group_states=100000,total_states=2000000,wall_seconds=120,max_output_bytes=50000000)

def summary(rows):
    return dict(paths=len(rows),states=rows[0]['states_explored'],safe=all(r['metrics']['duplicate_effects']==0 for r in rows),complete=all(r['metrics']['actual_complete'] for r in rows),justified=all(r['metrics']['justified_complete'] for r in rows),max_calls=max(r['metrics']['calls'] for r in rows),min_return=min(r['metrics']['return_time'] for r in rows),max_return=max(r['metrics']['return_time'] for r in rows))

def check(rows):
    # The independent checker verifies safety basis for named adequate policies.
    # Relabel a COPY so its keyless certified-absence check is also applied here.
    checked=copy.deepcopy(rows)
    for r in checked:
        if r['policy']=='terminal_barrier':r['policy']='horizon_aware'
    return checker.validate_group(checked)

cases=[]
for T,lag,budget,offset,originals,outcome in itertools.product([2,4],[0,1,2],[1,2,3],[-1,0],itertools.product(['early','late','never'],repeat=2),['success','reject','timeout_commit']):
    c=dict(CASE,id=f'boundary-{len(cases):04}',original_terminal=T,late=T-1,lag=lag,budget=budget,deadline=T+max(lag,1)+offset,originals=list(originals),retry_outcome=outcome,horizon=T+lag+10)
    cases.append(c)
# Supplement exact witnesses for deadline cost, positive-only reconciliation,
# no-positive-evidence-on-timeout, and the falsified one-call shortcut.
extras=[dict(CASE,id='witness'),dict(CASE,id='short-positive-deadline',originals=['early','early'],deadline=3),dict(CASE,id='timeout-not-justified',retry_outcome='timeout_commit'),dict(CASE,id='one-call-insufficient',budget=1)]
allcases=cases+extras
(ROOT/'cases.json').write_text(json.dumps(allcases,indent=2,sort_keys=True)+'\n')
start=time.monotonic();states=0;paths=0;groups=[];pair_stats=Counter();witness={}
with gzip.open(ROOT/'paths.jsonl.gz','wt') as f:
    for c in allcases:
        pair={}
        for p in ['horizon_aware','terminal_barrier']:
            rows=model.simulate(c,p,max_states=BOUNDS['per_group_states'])
            s=summary(rows);s.update(case_id=c['id'],policy=p,coverage=check(rows))
            states+=s['states'];paths+=s['paths'];groups.append(s);pair[p]=s
            for row in rows:f.write(json.dumps(row,sort_keys=True)+'\n')
            if c['id'] in {e['id'] for e in extras}:witness.setdefault(c['id'],{})[p]=rows
            assert states<=BOUNDS['total_states'], 'incomplete state budget'
            assert time.monotonic()-start<=BOUNDS['wall_seconds'], 'incomplete wall budget'
            assert (ROOT/'paths.jsonl.gz').stat().st_size<=BOUNDS['max_output_bytes'], 'incomplete output budget'
        old,new=pair['horizon_aware'],pair['terminal_barrier']
        assert old['safe'] and new['safe']
        if c in cases:
            pair_stats['cases']+=1
            for k in ['complete','justified']:
                pair_stats[k+'_gain']+=int(new[k] and not old[k])
                pair_stats[k+'_loss']+=int(old[k] and not new[k])
            if c['budget']>=2 and c['deadline']>=c['original_terminal']+max(c['lag'],1) and c['retry_outcome']!='reject':
                assert new['complete'], ('boundary failed',c)
                pair_stats['theorem_condition_cases']+=1
                pair_stats['theorem_condition_paths']+=new['paths']
            if c['lag']>=1:assert all(old[k]==new[k] for k in ['safe','complete','justified','max_calls','min_return','max_return','paths'])
(ROOT/'groups.json').write_text(json.dumps(groups,indent=2,sort_keys=True)+'\n')
(ROOT/'witnesses.json').write_text(json.dumps(witness,indent=2,sort_keys=True)+'\n')
result=dict(status='complete',posthoc=True,source_commit='d301e982db65deed6c065063ac243a1e0c0888c7',source_pins=PINS,bounds=BOUNDS,total_cases=len(allcases),grid_cases=len(cases),total_groups=len(groups),total_states=states,total_paths=paths,wall_seconds=time.monotonic()-start,pair_statistics=dict(pair_stats),all_groups_independently_reconstructed_and_coverage_checked=True,limitation='Finite grid tests the unchanged published simulator; policy relabeling enables its independent certified-write safety check but does not constitute an independent implementation of the new policy. Analytic proof is separate.')
(ROOT/'RESULT.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result,indent=2))
