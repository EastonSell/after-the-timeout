"""Read-only saved-results recount, imports checker only (not model or runner)."""
import gzip,hashlib,json,resource,sys,time
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
import checker
out=Path(sys.argv[1]);start=time.monotonic();totals=defaultdict(lambda:defaultdict(int));groups={};paths=0
expected_group_summaries={(g['case_id'],g['policy']):g for g in map(json.loads,(out/'group-summaries.jsonl').read_text().splitlines())}
def process(rows):
    global paths
    if not rows:return
    c=rows[0]['case'];p=rows[0]['policy'];key=(c['id'],p)
    if key in groups:raise ValueError('noncontiguous repeated group')
    trace_hashes=[hashlib.sha256(json.dumps(r['hidden_trace'],sort_keys=True).encode()).hexdigest() for r in rows]
    if len(set(trace_hashes))!=len(trace_hashes):raise ValueError('duplicate terminal scheduler trace')
    coverage=checker.validate_group(rows)
    if expected_group_summaries[key]['coverage']!=coverage:raise ValueError('coverage certificate mismatch')
    groups[key]=coverage;paths+=len(rows);m=[r['metrics'] for r in rows];a=totals[c['family']+'|'+p]
    for k,v in dict(cases=1,paths=len(rows),unsafe_cases=int(any(x['duplicate_effects'] for x in m)),
        all_safe_cases=int(all(x['duplicate_effects']==0 for x in m)),all_actual_complete_cases=int(all(x['actual_complete'] for x in m)),
        any_actual_complete_cases=int(any(x['actual_complete'] for x in m)),all_justified_cases=int(all(x['justified_complete'] for x in m)),
        post_return_unsafe_cases=int(any(x['post_return_duplicate_effects'] for x in m))).items():a[k]+=v
with gzip.open(out/'rows.jsonl.gz','rt') as f:
    current=[];last=None
    for line in f:
        row=json.loads(line);key=(row['case']['id'],row['policy'])
        if last is not None and key!=last:process(current);current=[]
        current.append(row);last=key
    process(current)
expected={(c['id'],p) for c in json.loads((ROOT/'cases.json').read_text()) for p in ['naive_inspection','blind_keyed','capability_fallback','horizon_aware']}
if set(groups)!=expected:raise ValueError('missing/extra case-policy groups')
summary=json.loads((out/'summary.json').read_text())
if dict(totals)!=summary['totals'] or paths!=summary['paths']:raise ValueError('aggregate recount mismatch')
result=dict(passed=True,groups=len(groups),paths=paths,totals=dict(totals),
    coverage_manifest_sha256=hashlib.sha256(json.dumps(sorted((list(k),v) for k,v in groups.items()),sort_keys=True).encode()).hexdigest(),
    elapsed_seconds=time.monotonic()-start,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    imports_simulator=False,network_requests=0,processes=1)
with open(out/'independent-recount.json','x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='totals'},sort_keys=True))
