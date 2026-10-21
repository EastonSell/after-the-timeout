import json,platform,random
from pathlib import Path
from workflow import Service,execute

def run():
 cfg=json.loads(Path('config.json').read_text());rows=[]
 for seed in cfg['seeds']:
  rng=random.Random(seed)
  scenarios=[(fault,status,idem) for fault in cfg['faults'] for status in [True,False] for idem in [True,False]]
  rng.shuffle(scenarios)
  for fault,status,idem in scenarios:
   for policy in ['blind_retry','inspect_first']:
    s=Service(fault,status,idem);outcome=execute(s,policy)
    rows.append(dict(seed=seed,fault=fault,status_supported=status,idempotent=idem,policy=policy,outcome=outcome,calls=s.calls,commits=len(s.records),duplicate_commits=max(0,len(s.records)-1)))
 summary={p:{'runs':len([r for r in rows if r['policy']==p]),'duplicates':sum(r['duplicate_commits'] for r in rows if r['policy']==p),'unresolved':sum(r['outcome']=='needs_reconciliation' for r in rows if r['policy']==p),'calls':sum(r['calls'] for r in rows if r['policy']==p)} for p in ['blind_retry','inspect_first']}
 Path('results/experiment.json').write_text(json.dumps({'measurement_type':'deterministic offline fault simulation','python':platform.python_version(),'config':cfg,'summary':summary,'rows':rows},indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':run()
