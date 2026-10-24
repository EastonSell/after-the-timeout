import sys,json,gzip,copy,hashlib,itertools
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from vendor import model,checker
import policies
OUT=Path(__file__).resolve().parent

def independent_action(v):
 c=v['contract'];t=v['now'];missing=set(('A','B'))-set(v['known'])
 if not missing:return {'kind':'stop','reason':'positive evidence for all items'}
 if v['calls']>=c['budget'] or t>c['deadline']:return {'kind':'stop','reason':'resource limit'}
 if c['observation']=='unavailable':return {'kind':'stop','reason':'no evidence interface'}
 if v['observations'] and v['observations'][-1]['write_count']==v['writes']:
  targets=[i for i in v['observations'][-1]['terminal_absent'] if i in missing]
  if targets:return dict(kind='write',targets=targets,keyed=False,reason='certified terminal absence')
  if c['observation']=='opaque':return dict(kind='stop',reason='negative is not terminal evidence')
 b=max(c['original_terminal'],v['last_write_bound'])
 # Preserve old early stop before applying barrier, as implementation does.
 old_start=max(t,b+c['lag']-1)
 if old_start>c['deadline']:return dict(kind='stop',reason='terminal snapshot exceeds action deadline')
 start=max(t,b+(max(c['lag'],1) if c['observation']=='certified' else c['lag'])-1)
 if start>c['deadline']:return dict(kind='stop',reason='barrier snapshot exceeds action deadline')
 return dict(kind='wait',until=start) if start>t else dict(kind='read')

def audit(row):
 c=row['case'];v=dict(contract={k:c[k] for k in ['scope','strategy','ttl','observation','lag','original_terminal','budget','deadline','horizon']},now=1,known=[],calls=0,actions=[],observations=[],replies=[],writes=0,last_write_bound=0)
 replies=iter(e['reply'] for e in row['public_trace'] if e['kind']=='reply');n=0
 for e in row['hidden_trace']:
  v['now']=e['t']
  if e['kind']=='event' and e['event']['kind']=='response':
   r=next(replies);v['replies'].append(r);v['known']=sorted(set(v['known'])|set(r['positive']))
  elif e['kind']=='observation':
   o=e['observation'];v['observations'].append(o);v['known']=sorted(set(v['known'])|set(o['positive']))
  elif e['kind']=='action':
   a=e['action'];assert a==independent_action(v),(c,a,independent_action(v));n+=1
   if a['kind'] in ('read','write'):
    v['calls']+=1;v['actions'].append(dict(t=e['t'],**a))
   if a['kind']=='write':v['writes']+=1;v['last_write_bound']=e['t']+4
 return n
rows=[json.loads(l) for l in gzip.open(ROOT/'paths.jsonl.gz','rt')]
new=[r for r in rows if r['policy']=='terminal_barrier']
actions=sum(audit(r) for r in new)
# exact rerun compare excluding timing resource measurement
old=json.loads((ROOT/'RESULT.json').read_text());repeat=json.loads((OUT/'reproduction/RESULT.json').read_text());old.pop('wall_seconds');repeat.pop('wall_seconds');assert old==repeat
assert gzip.decompress((ROOT/'paths.jsonl.gz').read_bytes())==gzip.decompress((OUT/'reproduction/paths.jsonl.gz').read_bytes())
# Independent test of checker coverage rejection on witness with missing scheduler paths.
w=[r for r in new if r['case']['id']=='witness'];partial_rejected=False
try:checker.validate_group(w[:1])
except ValueError:partial_rejected=True
assert partial_rejected
# Additional new cross-contract/range stress: not held out, not a frequency estimate.
extra_cases=0;extra_paths=0;extra_actions=0
for T,lag,scope,obs,outcome,originals in itertools.product([1,3,7],[0,1,3],['none','item','batch'],['certified','opaque','unavailable'],['success','timeout_commit','reject'],[['never','never'],['early','never'],['late','late']]):
 c=dict(id='review-extra',family='review-posthoc',originals=originals,late=max(0,T-1),original_terminal=T,scope=scope,strategy='reserve',ttl=100,observation=obs,lag=lag,retry_outcome=outcome,budget=2,deadline=max(2,T+max(lag,1)),horizon=T+lag+10)
 rr=model.simulate(c,'terminal_barrier');extra_cases+=1;extra_paths+=len(rr)
 checked=copy.deepcopy(rr)
 for r in checked:r['policy']='horizon_aware'
 checker.validate_group(checked)
 for r in rr:
  extra_actions+=audit(r);assert r['metrics']['duplicate_effects']==0
  if obs=='certified' and outcome!='reject':assert r['metrics']['actual_complete']
result=dict(status='passed',reproduced_exact_paths=len(rows),audited_candidate_paths=len(new),audited_candidate_decisions=actions,missing_scheduler_branch_rejected=partial_rejected,additional_cases=extra_cases,additional_paths=extra_paths,additional_decisions=extra_actions,limitations='Separate decision specification plus original independent environment checker; extra post-hoc tests are not held-out validation or universal proof.')
(OUT/'audit-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
