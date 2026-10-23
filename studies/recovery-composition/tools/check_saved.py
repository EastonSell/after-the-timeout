"""Portable saved-data check, derived from tools/recount_saved.py.

This checks dynamics/evidence/coverage and manifest identity, not whether a named
policy would choose each action. No simulator import or new scientific run.
The inputs are read-only; an optional report must be a fresh file outside them.
"""
import argparse,gzip,hashlib,json,sys,time
try:
    import resource
except ImportError:
    resource=None
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'source'))
import checker
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('saved_root',type=Path,help='fresh reconstructed study root')
parser.add_argument('--report',type=Path,help='optional fresh JSON file outside saved_root')
args=parser.parse_args()
saved_root=args.saved_root.resolve();out=saved_root/'results-v1'
if args.report and (args.report.resolve().is_relative_to(saved_root) or args.report.exists() or args.report.is_symlink()):
    raise ValueError('report must be a fresh file outside the input tree')
manifest={c['id']:c for c in json.loads((ROOT/'cases.json').read_text())}
start=time.monotonic();totals=defaultdict(lambda:defaultdict(int));groups={};paths=0
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
        if row['case']!=manifest.get(row['case']['id']):raise ValueError('row case differs from accepted manifest')
        if last is not None and key!=last:process(current);current=[]
        current.append(row);last=key
    process(current)
expected={(c['id'],p) for c in json.loads((ROOT/'cases.json').read_text()) for p in ['naive_inspection','blind_keyed','capability_fallback','horizon_aware']}
if set(groups)!=expected:raise ValueError('missing/extra case-policy groups')
summary=json.loads((out/'summary.json').read_text())
if dict(totals)!=summary['totals'] or paths!=summary['paths']:raise ValueError('aggregate recount mismatch')
result=dict(passed=True,groups=len(groups),paths=paths,totals=dict(totals),
    coverage_manifest_sha256=hashlib.sha256(json.dumps(sorted((list(k),v) for k,v in groups.items()),sort_keys=True).encode()).hexdigest(),
    elapsed_seconds=time.monotonic()-start,max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None,
    imports_simulator=False,network_requests=0,processes=1)
result['scope']='dynamics/evidence/coverage and exact manifest identities; not registered-policy choice replay'
if args.report:
    with args.report.open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({k:v for k,v in result.items() if k!='totals'},sort_keys=True))
